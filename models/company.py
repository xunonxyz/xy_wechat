from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

    we_corp_id = fields.Char(string='Corp ID', required=True, default='Wechat Enterprise corp id')
    app_ids = fields.One2many('wechat.enterprise.app', 'company_id', string='Apps')
    # use in WE callback
    we_cb_token = fields.Char(string='Token')
    we_cb_encoding_AES_key = fields.Char(string='EncodingAESKey')
    # use in WE oa callback
    we_oa_cb_token = fields.Char(string='Token')
    we_oa_cb_encoding_AES_key = fields.Char(string='EncodingAESKey')

    def on_oa_callback(self, xml_tree):
        """
        callback when wechat enterprise oa event, you can override this method to do something
        :param xml_tree: callback info by xml, you can get attribute by xml_tree.find('xxx').find('xxx').text
        :return:
        """
        pass
