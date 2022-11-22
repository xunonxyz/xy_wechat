# -*- coding: utf-8 -*-
import asyncio
import base64
from urllib import parse
import warnings
import xml.etree.cElementTree as ET

from odoo import http
from odoo.http import route, request
from ..common.we_request import we_request_instance, join_url
from ..common.callback.WXBizMsgCrypt import WXBizMsgCrypt

# Crypto will show warning, ignore it
warnings.filterwarnings("ignore", category=DeprecationWarning)


class WechatEnterpriseController(http.Controller):
    scan_oauth_url = 'https://open.work.weixin.qq.com/wwopen/sso/qrConnect?appid={corp_id}&agentid={agentid}&redirect_uri={redirect_uri}'
    web_oauth_url = 'https://open.weixin.qq.com/connect/oauth2/authorize?appid={corp_id}&redirect_uri={redirect_uri}&response_type=code&scope={scope}&agentid={agentid}#wechat_redirect'

    @classmethod
    def force_authenticate(cls, session, user):
        session.pre_uid = user.id
        session.pre_login = user.login
        if not user._mfa_url():
            session.finalize(request.env)
        user._update_last_login()

    @http.route('/WW_verify_<string:filename>.txt', type='http', auth="none", methods=['GET'])
    def load_file(self, filename=None):
        """
        load verify file, easily to verify wechat enterprise redirect url
        :param filename:
        :return:
        """
        app = request.env['wechat.enterprise.app'].sudo().search(
            [('verify_txt_filename', '=', f'WW_verify_{filename}.txt')],
            limit=1
        )
        if len(app) == 0:
            content = None
        else:
            content = base64.b64decode(app[0].verify_txt).decode('utf-8')
        return content

    @route('/we/oauth2/info', type='json', auth='public')
    def get_we_oauth2_info(self, app_id, redirect_uri=None):
        """
        get info for build Wechat Enterprise QRCode to login
        :param app_id:
        :param redirect_uri: redirect url after login, don't need host
        :return:
        """
        app = request.env['wechat.enterprise.app'].sudo().browse(int(app_id))
        host = request.httprequest.host_url
        return {
            'agentid': app.agentid,
            'corp_id': app.corp_id,
            'redirect_uri': join_url(host, f'we/oauth2/login/{app_id}') if redirect_uri is None else
            join_url(host, redirect_uri)
        }

    @route('/we/oauth2/login/<int:app_id>', type='http', auth='public')
    def login_by_oauth2(self, code, app_id):
        """
        login by wechat enterprise oauth2
        :param code:
        :param app_id:
        :return:
        """
        app = request.env['wechat.enterprise.app'].sudo().browse(int(app_id))
        we_request = we_request_instance(app.corp_id, app.secret)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        get_userid_task = loop.create_task(we_request.get_userid(code))
        loop.run_until_complete(get_userid_task)
        loop.close()
        we_id = get_userid_task.result()
        employee = request.env['hr.employee'].sudo().search([('we_id', '=', we_id)])
        if employee.user_id.id:
            self.force_authenticate(request.session, employee.user_id)
            return request.redirect('/web')

    @route('/we/oauth2/build/<string:oauth_type>/<int:app_id>', type='http', auth='public')
    def we_oauth2(self, oauth_type, app_id, scope='snsapi_base'):
        """
        build wechat enterprise oauth2 url
        :param oauth_type: scan or web, scan is build to qrcode, web is build to redirect url
        :param app_id: authenticate used app id
        :param scope: snsapi_base or snsapi_privateinfo
        :return:
        """
        oauth2_info = self.get_we_oauth2_info(app_id)
        corp_id = oauth2_info['corp_id']
        agentid = oauth2_info['agentid']
        redirect_uri = parse.quote(oauth2_info['redirect_uri'])

        _redirect_uri = ''
        if oauth_type == 'scan':
            _redirect_uri = self.scan_oauth_url.format(
                corp_id=corp_id,
                agentid=agentid,
                redirect_uri=redirect_uri
            )
        elif oauth_type == 'web':
            _redirect_uri = self.web_oauth_url.format(
                corp_id=corp_id,
                agentid=agentid,
                redirect_uri=redirect_uri,
                scope=scope
            )
        return request.redirect(_redirect_uri, 303, False)

    @route('/we/mail_list/callback', type='http', auth='public', csrf=False)
    def we_callback(self, msg_signature, timestamp, nonce, echostr=''):
        if request.httprequest.method == 'GET':
            result = None
            company_list = request.env['res.company'].sudo().search([])
            for company in company_list:
                if company.we_cb_token and company.we_cb_encoding_AES_key:
                    wxcpt = WXBizMsgCrypt(company.we_cb_token, company.we_cb_encoding_AES_key, company.we_corp_id)
                    ret, s_echo_str = wxcpt.VerifyURL(msg_signature, timestamp, nonce, echostr)
                    if ret == 0:
                        result = s_echo_str
                        break
            return result
        else:
            data = request.httprequest.data.decode('utf-8')
            # get ToUserName to match company corp_id
            temp_xml_tree = ET.fromstring(data)
            corp_id = temp_xml_tree.find('ToUserName').text
            company = request.env['res.company'].sudo().search([('we_corp_id', '=', corp_id)])

            wxcpt = WXBizMsgCrypt(company.we_cb_token, company.we_cb_encoding_AES_key, company.we_corp_id)
            ret, result = wxcpt.DecryptMsg(data, msg_signature, timestamp, nonce)
            if ret == 0:
                xml_tree = ET.fromstring(result)
                change_type = xml_tree.find('ChangeType').text
                # change_type may be xxx_user or xxx_party
                suffix = change_type.split('_')[1]
                model = request.env['hr.employee'] if suffix == 'user' else request.env['hr.department']
                # method need return 'success' or empty string
                func = getattr(model, f'on_we_{change_type}', None)
                if func:
                    return func(xml_tree, company)
            return ''
