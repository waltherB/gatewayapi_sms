# -*- coding: utf-8 -*-

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class GatewayapiCleanup(models.AbstractModel):
    _name = 'gatewayapi.cleanup'
    _description = 'Cleanup utilities for GatewayAPI SMS module'

    @api.model
    def cleanup_iap_views(self):
        """Clean up IAP account views to remove GatewayAPI-specific elements"""
        _logger.info("Cleaning up IAP account views from GatewayAPI elements")
        
        # First, try to fix tree views
        tree_views = self.env['ir.ui.view'].search([
            ('model', '=', 'iap.account'),
            ('type', '=', 'tree'),
            ('arch_db', 'like', '%gatewayapi%')
        ])
        
        for view in tree_views:
            _logger.info(f"Cleaning up tree view {view.id} ({view.name})")
            try:
                # Remove decoration attributes with gatewayapi
                view.arch_db = view.arch_db.replace('decoration-info="provider == \'sms_api_gatewayapi\' or (gatewayapi_base_url != False and gatewayapi_api_token != False)"', '')
                
                # Remove fields
                view.arch_db = view.arch_db.replace('<field name="gatewayapi_base_url" invisible="1"/>', '')
                view.arch_db = view.arch_db.replace('<field name="gatewayapi_api_token" invisible="1"/>', '')
                view.arch_db = view.arch_db.replace('<field name="gatewayapi_balance_display"/>', '')
            except Exception as e:
                _logger.error(f"Error cleaning up tree view {view.id}: {e}")
        
        # Clean up form views
        form_views = self.env['ir.ui.view'].search([
            ('model', '=', 'iap.account'),
            ('type', '=', 'form'),
            ('arch_db', 'like', '%gatewayapi%')
        ])
        
        for view in form_views:
            _logger.info(f"Cleaning up form view {view.id} ({view.name})")
            try:
                # Try to replace the entire GatewayAPI group
                arch_db = view.arch_db
                start_tag = '<group string="GatewayAPI account" name="group_sms_api_gatewayapi"'
                end_tag = '</group>'
                
                start_index = arch_db.find(start_tag)
                if start_index >= 0:
                    # Find the closing tag by counting opening and closing group tags
                    depth = 1
                    end_index = start_index + len(start_tag)
                    
                    while depth > 0 and end_index < len(arch_db):
                        open_pos = arch_db.find('<group', end_index)
                        close_pos = arch_db.find('</group>', end_index)
                        
                        if open_pos >= 0 and (close_pos < 0 or open_pos < close_pos):
                            # Found an opening tag first
                            depth += 1
                            end_index = open_pos + 6  # len('<group')
                        elif close_pos >= 0:
                            # Found a closing tag
                            depth -= 1
                            end_index = close_pos + 8  # len('</group>')
                        else:
                            # Safety break
                            break
                    
                    if depth == 0:
                        # Found the matching closing tag, remove everything in between
                        arch_db = arch_db[:start_index] + arch_db[end_index:]
                        view.arch_db = arch_db
            except Exception as e:
                _logger.error(f"Error cleaning up form view {view.id}: {e}")
        
        return True 