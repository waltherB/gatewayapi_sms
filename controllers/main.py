import json
import logging
import jwt # For JWT decoding
from werkzeug.exceptions import Forbidden, Unauthorized, ServiceUnavailable # For HTTP errors
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class GatewayApiWebhookController(http.Controller):

    @http.route('/gatewayapi/dlr', type='json', auth='public', methods=['POST'], csrf=False)
    def gatewayapi_dlr_webhook(self, **kwargs):
        """Webhook to receive Delivery Reports (DLRs) from GatewayAPI."""

        # --- Start of JWT Verification ---
        auth_header = request.httprequest.headers.get('X-Gwapi-Signature')
        if not auth_header:
            _logger.warning("GatewayAPI DLR: Missing X-Gwapi-Signature header. Unauthorized.")
            raise Unauthorized("Missing X-Gwapi-Signature header.")

        jwt_secret = request.env['ir.config_parameter'].sudo().get_param('gatewayapi.webhook_jwt_secret')
        if not jwt_secret:
            _logger.error("GatewayAPI DLR: JWT secret not configured in Odoo (gatewayapi.webhook_jwt_secret). Service unavailable.")
            # Return 503 to indicate service is temporarily unavailable due to misconfiguration
            raise ServiceUnavailable("JWT secret not configured on server.")

        try:
            # The token is the value of the X-Gwapi-Signature header
            token = auth_header
            # GatewayAPI docs specify HS256 algorithm
            # This just decodes, doesn't validate claims like 'exp' by default unless options passed
            jwt.decode(token, jwt_secret, algorithms=['HS256'])
            _logger.info("GatewayAPI DLR: JWT verified successfully.")

        except jwt.ExpiredSignatureError:
            _logger.warning("GatewayAPI DLR: JWT verification failed - ExpiredSignatureError.")
            raise Unauthorized("Token has expired.")
        except jwt.InvalidTokenError as e:
            _logger.warning("GatewayAPI DLR: JWT verification failed - InvalidTokenError: %s", str(e))
            raise Forbidden("Invalid token.") # 403 as the token is malformed or signature mismatch
        except Exception as e:
            _logger.error("GatewayAPI DLR: An unexpected error occurred during JWT verification: %s", str(e))
            raise ServiceUnavailable("Error during token verification.")
        # --- End of JWT Verification ---

        # Now get the data, as JWT is valid
        data = request.jsonrequest
        # Log full data as string and specific ID for traceability
        _logger.info("GatewayAPI DLR Webhook received data (JWT verified): %s for message ID %s",
                     json.dumps(data), data.get('id'))


        gw_message_id = data.get('id')
        status = data.get('status') # e.g., DELIVERED, EXPIRED, UNDELIVERABLE, REJECTED
        error_description = data.get('error')
        # timestamp = data.get('time') # UNIX timestamp

        if not gw_message_id or not status:
            _logger.warning("GatewayAPI DLR: 'id' or 'status' missing in payload. Data: %s", data)
            return {'status': 'error', 'message': 'Missing id or status'}

        SmsMessage = request.env['sms.sms'].sudo()
        # Ensure gw_message_id is searched as a string, as it's stored as Char
        sms_message = SmsMessage.search([('gatewayapi_message_id', '=', str(gw_message_id))], limit=1)

        if not sms_message:
            _logger.warning("GatewayAPI DLR: No sms.sms record found for gatewayapi_message_id: %s", gw_message_id)
            # Returning 200 OK anyway so GatewayAPI doesn't keep retrying for a message we don't know
            return {'status': 'ok', 'message': 'SMS not found but acknowledged'}

        # Basic status mapping (can be expanded)
        # Odoo states: 'outgoing', 'sent', 'error', 'canceled'
        # GatewayAPI final states: DELIVERED, EXPIRED, UNDELIVERABLE, ACCEPTED, REJECTED, SKIPPED
        original_odoo_state = sms_message.state
        new_odoo_state = original_odoo_state
        failure_type = sms_message.failure_type # Preserve existing failure type unless overwritten

        if original_odoo_state in ['error', 'sent', 'canceled']: # Already a final Odoo state
             _logger.info(
                "GatewayAPI DLR: SMS ID %s (GW ID %s) already in final Odoo state '%s'. Received GW status '%s'. Ignoring update to Odoo state.",
                sms_message.id, gw_message_id, original_odoo_state, status
            )
             # Optional: could store additional error info if it's a new error for an already failed message
             # For example, if status is an error and original_odoo_state was 'sent'
             if status not in ['DELIVERED', 'ACCEPTED'] and original_odoo_state == 'sent':
                 _logger.info("GatewayAPI DLR: SMS ID %s (GW ID %s) was 'sent', but received error DLR '%s'. Setting to error.", sms_message.id, gw_message_id, status)
                 new_odoo_state = 'error'
                 if status == 'UNDELIVERABLE': failure_type = 'sms_unregistered'
                 elif status == 'REJECTED': failure_type = 'sms_blacklist'
                 else: failure_type = 'sms_other'
        else: # Typically 'outgoing' or 'queued' (if such a custom state existed)
            if status == 'DELIVERED' or status == 'ACCEPTED': # 'ACCEPTED' by network can be considered final by some
                new_odoo_state = 'sent' # Odoo 'sent' often means successfully delivered or accepted by recipient
                failure_type = False # Clear failure type on success
            elif status in ['EXPIRED', 'UNDELIVERABLE', 'REJECTED', 'SKIPPED']:
                new_odoo_state = 'error'
                # Attempt to map GatewayAPI status to Odoo's failure_type
                # Odoo failure_types: 'sms_number_format', 'sms_server', 'sms_credit', 'sms_blacklist', 'sms_duplicate', 'sms_optout', 'sms_unregistered', 'sms_other'
                if status == 'UNDELIVERABLE':
                    failure_type = 'sms_unregistered'
                elif status == 'REJECTED':
                    failure_type = 'sms_blacklist' # Or 'sms_other'
                elif status == 'EXPIRED': # Could be network issue or phone off for too long
                    failure_type = 'sms_other' # Consider a more specific type if available/needed
                else: # SKIPPED etc.
                    failure_type = 'sms_other'
            else: # Intermediate statuses like ENROUTE, BUFFERED, etc.
                _logger.info("GatewayAPI DLR: Received intermediate status '%s' for GW ID %s. Odoo state remains '%s'.",
                             status, gw_message_id, original_odoo_state)
                # We typically don't change Odoo state for these unless we add more granular states

        update_vals = {}
        if new_odoo_state != original_odoo_state:
            update_vals['state'] = new_odoo_state

        # Only update failure_type if new_odoo_state is 'error' and failure_type has changed or is being set
        if new_odoo_state == 'error' and (failure_type != sms_message.failure_type or not sms_message.failure_type):
             update_vals['failure_type'] = failure_type
        elif new_odoo_state == 'sent': # Clear failure type on success
            update_vals['failure_type'] = False


        if error_description and new_odoo_state == 'error':
            # Store the error description if provided and the message is marked as error
            # This could be appended to an existing field or stored in a new dedicated field.
            # For now, just logging it. A custom field like 'gateway_delivery_error_details' would be better.
            _logger.info("GatewayAPI DLR: Error details for GW ID %s (SMS ID %s): %s", gw_message_id, sms_message.id, error_description)
            # Example: update_vals['gateway_delivery_error_details'] = error_description


        if update_vals: # only write if there are changes
            sms_message.write(update_vals)
            _logger.info(
                "GatewayAPI DLR: Updated SMS ID %s (GW ID %s) to state '%s' (was '%s'). Failure type: '%s'. GW status: %s.",
                sms_message.id, gw_message_id, new_odoo_state, original_odoo_state, failure_type, status
            )
        elif new_odoo_state == original_odoo_state: # Log if state didn't change but DLR was processed
             _logger.info(
                "GatewayAPI DLR: SMS ID %s (GW ID %s) Odoo state '%s' unchanged by GW status '%s'. DLR processed.",
                sms_message.id, gw_message_id, original_odoo_state, status
            )

        # Acknowledge receipt to GatewayAPI
        return {'status': 'ok', 'message': 'DLR processed'}
