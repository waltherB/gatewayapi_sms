# -*- coding: utf-8 -*-

from odoo import fields, models, tools
import logging
import requests
import re
from odoo.http import request

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)


class Sms(models.Model):
    _inherit = "sms.sms"

    sms_api_error = fields.Char()
    gatewayapi_message_id = fields.Char(string="GatewayAPI Message ID", copy=False, readonly=True, index=True)

    def _prepare_gatewayapi_payload_item(self, iap_account, base_url):
        self.ensure_one()
        if not self.number: # Should be pre-validated, but as a safeguard
            return None

        # Emoji detection regex (covers most emoji ranges)
        # Moved from old _send_sms_with_gatewayapi
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002700-\U000027BF"  # Dingbats
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            "\U00002600-\U000026FF"  # Misc symbols
            "]+", flags=re.UNICODE)

        # Get the base URL for the webhook
        callback_url = f"{base_url}/gatewayapi/dlr"

        payload = {
            "sender": iap_account.gatewayapi_sender or iap_account.service_name or "Odoo",
            "message": self.body,
            "recipients": [{"msisdn": int(self.number)}], # Assuming self.number is sanitized
            "userref": self.uuid,
            "callback_url": callback_url
        }

        if emoji_pattern.search(self.body):
            payload["encoding"] = "UCS2"

        return payload

def _send(self, unlink_failed=False, unlink_sent=True, raise_exception=False):
    """
    This method tries to send SMS after checking the number (presence and formatting).
    For GatewayAPI, it now sends messages in batches.
    """
    if self._is_sent_with_gatewayapi():
        results = []
        iap_account = self.env['iap.account']._get_sms_account()

        if not iap_account or not iap_account.gatewayapi_api_token or not iap_account.gatewayapi_base_url:
            _logger.error("GatewayAPI: Account not configured or missing token/base_url.")
            for sms_record in self:
                sms_record.sms_api_error = "GatewayAPI account misconfiguration"
                results.append({'uuid': sms_record.uuid, 'state': 'server_error'})
            self._postprocess_iap_sent_sms(results, unlink_failed=unlink_failed, unlink_sent=unlink_sent)
            return

        batch_payload_items = []
        sms_records_in_batch = self.env['sms.sms'] # To keep track of records for response mapping

        base_url = request.httprequest.url_root.rstrip('/')  # Get the base URL for the webhook

        for sms_record in self:
            if not sms_record.number:
                _logger.warning(f"SMS {sms_record.uuid} has no number, skipping.")
                results.append({'uuid': sms_record.uuid, 'state': 'wrong_number_format'})
                sms_record.sms_api_error = "Missing recipient number"
                continue # Skip this record from batch

            payload_item = sms_record._prepare_gatewayapi_payload_item(iap_account, base_url)
            if payload_item:
                batch_payload_items.append(payload_item)
                sms_records_in_batch |= sms_record
            else: # Should not happen if number check is done
                results.append({'uuid': sms_record.uuid, 'state': 'server_error'})
                sms_record.sms_api_error = "Payload preparation failed"

            if not batch_payload_items: # All records in self might have been skipped
                if results: # If some were skipped due to no number
                     self._postprocess_iap_sent_sms(results, unlink_failed=unlink_failed, unlink_sent=unlink_sent)
                # else: no records to process, no results to postprocess.
                return

            url = iap_account.gatewayapi_base_url.rstrip('/') + '/rest/mtsms?extra_details=recipients_usage'
            token = iap_account.gatewayapi_api_token

            try:
                _logger.debug(f"Sending SMS batch to GatewayAPI: url={url}, count={len(batch_payload_items)}")
                response = requests.post(url, json=batch_payload_items, auth=(token, ""))
                response.raise_for_status() # Raises HTTPError for 4xx/5xx
                response_content = response.json()
                _logger.debug(f"GatewayAPI batch response: {response_content}")

                # Process successful batch submission response
                # Priority 1: Use 'details' with 'userref' for mapping
                if response_content.get('details') and 'messages' in response_content['details']:
                    # This is the ideal scenario with userref mapping
                    responded_sms_map = {
                        item['userref']: {
                            'gw_msg_id': item.get('id'),
                            'status_text': item.get('recipients', [{}])[0].get('status'), # First recipient status
                            'error_code': item.get('recipients', [{}])[0].get('error_code'),
                            'accepted': item.get('recipients', [{}])[0].get('status') == 'SENT_OK' # Example
                        } for item in response_content['details']['messages'] if 'userref' in item
                    }

                    for sms_record in sms_records_in_batch:
                        res_item = responded_sms_map.get(sms_record.uuid)
                        if res_item:
                            sms_record.gatewayapi_message_id = str(res_item['gw_msg_id']) if res_item['gw_msg_id'] else None
                            if res_item['accepted']:
                                results.append({'uuid': sms_record.uuid, 'state': 'success'})
                                sms_record.sms_api_error = False
                            else:
                                results.append({'uuid': sms_record.uuid, 'state': 'server_error'})
                                sms_record.sms_api_error = f"Error {res_item['error_code']}: {res_item['status_text']}"
                        else:
                            # Message sent in batch but no corresponding item in 'details' with userref
                            results.append({'uuid': sms_record.uuid, 'state': 'server_error'})
                            sms_record.sms_api_error = "GatewayAPI response missing details for this SMS (userref)"
                            _logger.warning(f"SMS {sms_record.uuid} not found in GatewayAPI 'details' response with userref.")

                # Priority 2: Use 'ids' list and assume order if 'details' is not as expected
                elif response_content.get('ids') and len(response_content['ids']) == len(sms_records_in_batch):
                    _logger.info("GatewayAPI batch response: using 'ids' list and assuming order for mapping.")
                    for idx, sms_record in enumerate(sms_records_in_batch):
                        gw_msg_id = response_content['ids'][idx]
                        sms_record.gatewayapi_message_id = str(gw_msg_id)
                        # Assuming direct 'ids' list implies acceptance by gateway for all
                        results.append({'uuid': sms_record.uuid, 'state': 'success'})
                        sms_record.sms_api_error = False

                else: # Unexpected response structure
                    _logger.error(f"GatewayAPI batch response structure not recognized or mismatched: {response_content}")
                    for sms_record in sms_records_in_batch:
                        results.append({'uuid': sms_record.uuid, 'state': 'server_error'})
                        sms_record.sms_api_error = "GatewayAPI: Unrecognized batch response"

            except requests.exceptions.RequestException as e:
                _logger.error(f"GatewayAPI batch error: {e}, response: {getattr(e, 'response', None)}")
                error_message = f"GatewayAPI RequestException: {str(e)}"
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_details = e.response.json()
                        error_message += f" - Details: {error_details}"
                    except ValueError: # If response is not JSON
                        error_message += f" - Content: {e.response.text}"

                for sms_record in sms_records_in_batch: # Use sms_records_in_batch here
                    sms_record.sms_api_error = error_message
                    results.append({'uuid': sms_record.uuid, 'state': 'server_error'})
                if raise_exception: # Should this be inside or outside the loop? Usually outside for batch.
                    raise

            # Ensure results are complete for all original `self` records, including those skipped earlier
            processed_uuids = {r['uuid'] for r in results}
            for sms_record in self:
                if sms_record.uuid not in processed_uuids:
                    # This case should ideally be covered by the initial skipping or error handling
                    # but as a safeguard if a record from `self` was not added to `sms_records_in_batch`
                    # and also not explicitly handled with an error state in `results`.
                    _logger.warning(f"SMS {sms_record.uuid} was in original batch but not processed. Marking as error.")
                    results.append({'uuid': sms_record.uuid, 'state': 'server_error'})
                    sms_record.sms_api_error = "Unprocessed in batch"


            _logger.info('Send batch %s SMS via GatewayAPI: %s gave %s results', len(self.ids), self.ids, len(results))
            self._postprocess_iap_sent_sms(results, unlink_failed=unlink_failed, unlink_sent=unlink_sent)

        else: # Not GatewayAPI
            return super()._send(
                unlink_failed=unlink_failed, unlink_sent=unlink_sent,
                raise_exception=raise_exception)

    def _is_sent_with_gatewayapi(self):
        account = self.env['iap.account']._get_sms_account()
        # Check explicitly for GatewayAPI provider or configuration
        return account and account.provider == 'sms_api_gatewayapi' and \
               account.gatewayapi_base_url and account.gatewayapi_api_token
               # Made this check more stringent to ensure account is usable

    def _split_batch(self):
        if self._is_sent_with_gatewayapi():
            # GatewayAPI supports batch sending up to 1000 messages.
            # Using a smaller batch size for Odoo operations.
            batch_size = 200  # Or make this configurable later

            all_ids = self.ids
            for i in range(0, len(all_ids), batch_size):
                yield all_ids[i:i + batch_size]
        else:
            # Use 'yield from' to correctly delegate to the parent method
            yield from super()._split_batch()

    def _postprocess_iap_sent_sms(self, results, unlink_failed=False, unlink_sent=True):
        # Defensive: ensure all 'state' values are strings
        for result in results:
            if not isinstance(result.get('state'), str):
                _logger.error(f"Result with non-string state: {result}")
                result['state'] = str(result.get('state'))
        results_uuids = [result['uuid'] for result in results]
        all_sms_sudo = self.env['sms.sms'].sudo().search([('uuid', 'in', results_uuids)]).with_context(sms_skip_msg_notification=True)

        for iap_state, results_group in tools.groupby(results, key=lambda result: result['state']):
            sms_sudo = all_sms_sudo.filtered(lambda s: s.uuid in {result['uuid'] for result in results_group})
            if success_state := self.IAP_TO_SMS_STATE_SUCCESS.get(iap_state):
                sms_sudo.sms_tracker_id._action_update_from_sms_state(success_state)
                to_delete = {'to_delete': True} if unlink_sent else {}
                sms_sudo.write({'state': success_state, 'failure_type': False, **to_delete})
            else:
                failure_type = self.IAP_TO_SMS_FAILURE_TYPE.get(iap_state, 'unknown')
                if failure_type != 'unknown':
                    sms_sudo.sms_tracker_id._action_update_from_sms_state('error', failure_type=failure_type)
                else:
                    sms_sudo.sms_tracker_id._action_update_from_provider_error(iap_state)
                to_delete = {'to_delete': True} if unlink_failed else {}
                sms_sudo.write({'state': 'error', 'failure_type': failure_type, **to_delete})

        all_sms_sudo.mail_message_id._notify_message_notification_update()
