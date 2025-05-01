# -*- coding: utf-8 -*-

from odoo import fields, models, tools
import logging
import requests

_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class Sms(models.Model):
    _inherit = "sms.sms"

    sms_api_error = fields.Char()

    def _prepare_gatewayapi_payload(self, iap_account):
        self.ensure_one()
        return {
            "sender": iap_account.gatewayapi_sender or iap_account.service_name or "Odoo",
            "recipient": int(self.number),
            "message": self.body,
        }

    def _send(self, unlink_failed=False, unlink_sent=True, raise_exception=False):
        """ This method tries to send SMS after checking the number (presence and
        formatting). """
        if self._is_sent_with_gatewayapi():
            try:
                results = [sms._send_sms_with_gatewayapi() for sms in self]
            except Exception as e:
                _logger.warning('Sent batch %s SMS: %s: failed with exception %s', len(self.ids), self.ids, e)
                if raise_exception:
                    raise
                results = [{'uuid': sms.uuid, 'state': 'server_error'} for sms in self]
            else:
                _logger.info('Send batch %s SMS: %s: gave %s', len(self.ids), self.ids, results)
            self._postprocess_iap_sent_sms(results, unlink_failed=unlink_failed, unlink_sent=unlink_sent)
        else:
            return super()._send(
                unlink_failed=unlink_failed, unlink_sent=unlink_sent,
                raise_exception=raise_exception)

    def _is_sent_with_gatewayapi(self):
        return self.env['iap.account']._get_sms_account().provider == "sms_api_gatewayapi"

    def _send_sms_with_gatewayapi(self):
        self.ensure_one()
        if not self.number:
            return {"uuid": self.uuid, "state": "wrong_number_format"}

        iap_account_sms = self.env['iap.account']._get_sms_account()
        headers = {
            'Authorization': f'Token {iap_account_sms.gatewayapi_api_token}',
            'Content-Type': 'application/json',
        }
        url = iap_account_sms.gatewayapi_base_url.rstrip('/') + '/mobile/single'
        payload = self._prepare_gatewayapi_payload(iap_account_sms)
        response = requests.post(url, json=payload, headers=headers)

        try:
            response_content = response.json()
        except Exception:
            _logger.error(f"GatewayAPI non-JSON response: {response.text}")
            self.sms_api_error = response.text
            return {"uuid": self.uuid, "state": "server_error"}

        _logger.debug(f"GatewayAPI responded with: {response_content}")

        if response.status_code == 202 and 'msg_id' in response_content:
            _logger.info("SMS sent successfully")
            self.sms_api_error = False
            return {"uuid": self.uuid, "state": "success"}

        error_msg = response_content.get("error") or \
            response_content.get("detail") or str(response_content)
        _logger.warning(f"Failed to send SMS: {error_msg}")
        self.sms_api_error = error_msg
        return {"uuid": self.uuid, "state": "server_error"}

    def _split_batch(self):
        if self._is_sent_with_gatewayapi():
            # No batch
            for record in self:
                yield [record.id]
        else:
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
