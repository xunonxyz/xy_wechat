import asyncio
import threading
import time
import datetime
import traceback

from odoo import models, fields, api
from odoo.tools.translate import _

from ..common.we_request import we_request_instance


def get_now_time_str():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class App(models.Model):
    _name = 'wechat.enterprise.app'
    _description = 'Wechat Enterprise App'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    corp_id = fields.Char(string='Corp ID', related='company_id.we_corp_id', readonly=True)
    secret = fields.Char(string='Secret', required=True)
    agentid = fields.Char(string='Agent ID', required=True)
    sync_with_user = fields.Boolean(string='Sync with res.user', default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    # use in verify url
    verify_txt_filename = fields.Char(string='Verify Txt Filename', readonly=True)
    verify_txt = fields.Binary('verify_txt')

    def run_sync(self):
        self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
            'title': 'Sync Start......',
            'message': _('Start sync organization now, please wait......'),
            'warning': True
        })

        # create a threading to avoid odoo ui blocking
        def _sync():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            asyncio.run(self.sync_organization())

        thread = threading.Thread(target=_sync)
        thread.start()

    async def sync_organization(self):
        start = time.time()
        uid = self.env.uid
        is_success = True
        with self.env.registry.cursor() as new_cr:
            self.env = api.Environment(new_cr, uid, self.env.context)

            detail_log = f'start sync at {get_now_time_str()}......'
            try:
                we_request = we_request_instance(self.corp_id, self.secret)

                await self.env['hr.department'].with_context(
                    self.env.context, we_app=self, we_request=we_request
                ).sync_department()
                detail_log += f'\nsync success!'
            except Exception:
                is_success = False
                detail_log += f'\nsync failed, error: \n{traceback.format_exc()}'
            finally:
                detail_log += f'\nsync end at {get_now_time_str()}, cost {round(time.time() - start, 2)}s'
                company_id = self.company_id.id
                self.env['wechat.enterprise.log'].create({
                    'company_id': company_id,
                    'we_app_id': self.id,
                    'detail': detail_log
                })
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'title': 'Sync End......',
                    'message': f'Sync organization end, {"success" if is_success else "failed"}',
                    'warning': True if is_success else False
                })

    def upload_media(self, app_id, media_type, file_content, filename):
        """
        upload temp media to wechat server
        :param app_id: save at which app server
        :param media_type: image, voice, video, file
        :param file_content: file content bytes
        :param filename: file name
        :return: media_id in wechat server
        """
        app = self.env['wechat.enterprise.app'].sudo().browse(int(app_id))
        we_request = we_request_instance(app.corp_id, app.secret)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        upload_media_task = loop.create_task(we_request.upload_media(media_type, file_content, filename))
        loop.run_until_complete(upload_media_task)
        loop.close()
        return upload_media_task.result()

    def upload_image(self, app_id, file_content, filename):
        """
        upload permanently image to wechat server
        :param app_id: save at which app server
        :param file_content: file content bytes
        :param filename: file name
        :return: file_url in wechat server
        """
        app = self.env['wechat.enterprise.app'].sudo().browse(int(app_id))
        we_request = we_request_instance(app.corp_id, app.secret)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        upload_img_task = loop.create_task(we_request.upload_image(file_content, filename))
        loop.run_until_complete(upload_img_task)
        loop.close()
        return upload_img_task.result()

    def get_media(self, app_id, media_id):
        """
        get media from wechat server
        :param app_id: save in which app server
        :param media_id: media id in wechat server
        :return: file content bytes
        """
        app = self.env['wechat.enterprise.app'].sudo().browse(int(app_id))
        we_request = we_request_instance(app.corp_id, app.secret)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        get_media_task = loop.create_task(we_request.get_media(media_id))
        loop.run_until_complete(get_media_task)
        loop.close()
        return get_media_task.result()

    def get_oa_template_detail(self, app_id, template_id):
        """
        get oa template detail from wechat server
        :param app_id: save in which app server
        :param template_id: template id in wechat server
        :return: template detail
        """
        app = self.env['wechat.enterprise.app'].sudo().browse(int(app_id))
        we_request = we_request_instance(app.corp_id, app.secret)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        get_oa_template_detail_task = loop.create_task(we_request.get_oa_template_detail(template_id))
        loop.run_until_complete(get_oa_template_detail_task)
        loop.close()
        return get_oa_template_detail_task.result()

    def get_oa_approve_list(self, app_id, start_time, end_time, cursor=0, size=100, filters=None):
        """
        get oa approve list from wechat server
        :param app_id: save in which app server
        :param start_time: start time
        :param end_time: end time
        :param cursor: cursor
        :param size: size
        :param filters: filters
        :return: approve list
        """
        app = self.env['wechat.enterprise.app'].sudo().browse(int(app_id))
        we_request = we_request_instance(app.corp_id, app.secret)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        get_oa_approve_list_task = loop.create_task(
            we_request.get_oa_approve_list(start_time, end_time, cursor, size, filters))
        loop.run_until_complete(get_oa_approve_list_task)
        loop.close()
        return get_oa_approve_list_task.result()

    def get_oa_approve_detail(self, app_id, sp_no):
        """
        get oa approve detail from wechat server
        :param app_id: save in which app server
        :param sp_no: sp_no from get_oa_approve_info
        :return: approve detail
        """
        app = self.env['wechat.enterprise.app'].sudo().browse(int(app_id))
        we_request = we_request_instance(app.corp_id, app.secret)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        get_oa_approve_detail_task = loop.create_task(we_request.get_oa_approve_detail(sp_no))
        loop.run_until_complete(get_oa_approve_detail_task)
        loop.close()
        return get_oa_approve_detail_task.result()

    def get_corp_vacation_config(self, app_id):
        """
        get corp vacation config from wechat server
        :param app_id: save in which app server
        :return: vacation config
        """
        app = self.env['wechat.enterprise.app'].sudo().browse(int(app_id))
        we_request = we_request_instance(app.corp_id, app.secret)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        get_corp_vacation_config_task = loop.create_task(we_request.get_corp_vacation_config())
        loop.run_until_complete(get_corp_vacation_config_task)
        loop.close()
        return get_corp_vacation_config_task.result()

    def get_user_vacation_quota(self, app_id, userid):
        """
        get user vacation quota from wechat server
        :param app_id: save in which app server
        :param userid: wechat enterprise user id, not odoo id
        :return: vacation quota
        """
        app = self.env['wechat.enterprise.app'].sudo().browse(int(app_id))
        we_request = we_request_instance(app.corp_id, app.secret)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        get_user_vacation_quota_task = loop.create_task(we_request.get_user_vacation_quota(userid))
        loop.run_until_complete(get_user_vacation_quota_task)
        loop.close()
        return get_user_vacation_quota_task.result()

    def apply_oa_event(self, app_id, apply_data):
        """
        apply oa event from wechat server
        :param app_id: save in which app server
        :param apply_data: reference https://developer.work.weixin.qq.com/document/path/91853
        :return: apply result
        """
        app = self.env['wechat.enterprise.app'].sudo().browse(int(app_id))
        we_request = we_request_instance(app.corp_id, app.secret)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        apply_oa_event_task = loop.create_task(we_request.apply_oa_event(apply_data))
        loop.run_until_complete(apply_oa_event_task)
        loop.close()
        return apply_oa_event_task.result()
