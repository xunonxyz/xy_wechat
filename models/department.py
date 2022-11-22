import asyncio

from odoo import models, fields


class Department(models.Model):
    _inherit = 'hr.department'

    we_id = fields.Char(string='Wechat Enterprise Department ID')
    we_parent_id = fields.Char(string='Wechat Enterprise Parent Department ID')
    we_order = fields.Integer(string='Wechat Enterprise Department Order')
    '''because a Wechat Enterprise user can have multi departments, so we need a many2many field, 
    the department_id field is only main department'''
    we_employee_ids = fields.Many2many('hr.employee', 'we_employee_department_rel', 'department_id', 'employee_id',
                                       string='Wechat Enterprise Employees')

    async def get_server_depart_tree(self):
        """
        get Wechat Enterprise server department tree, root parentid is 1
        :return:
        """
        we_request = self.env.context.get('we_request')
        departments = await we_request.department_simplelist()

        def get_children(arr, parent_id):
            tree = []
            for item in arr:
                if item['parentid'] == parent_id:
                    tree.append({
                        'id': item['id'],
                        'parentid': item['parentid'],
                        'order': item['order'],
                        'children': get_children(arr, item['id'])
                    })

            return tree

        departments_tree = []

        for dep in departments:
            parents = list(filter(lambda x: x['id'] == dep['parentid'], departments))
            if len(parents) == 0:
                # this is root department
                departments_tree.append({
                    'id': dep['id'],
                    'parentid': dep['parentid'],
                    'order': dep['order'],
                    'children': get_children(departments, dep['id'])
                })

        return departments_tree

    async def sync_department(self):
        """
        sync department from wechat enterprise
        :return:
        """
        we_request = self.env.context.get('we_request')
        we_app = self.env.context.get('we_app')

        depart_tree = await self.get_server_depart_tree()

        tasks = []

        async def _sync_dep(server_dep, parent_id):
            _tasks = []
            dep_detail = await we_request.department_detail(server_dep['id'])

            dep = self.search([('we_id', '=', dep_detail['id'])])
            # dep need commit to db because sync user need use it
            modify_data = {
                'company_id': we_app.company_id.id,
                'name': dep_detail['name'],
                'we_id': dep_detail['id'],
                'parent_id': parent_id,
                'we_parent_id': dep_detail['parentid'],
                'we_order': dep_detail['order'],
                'manager_id': False
            }

            if dep.id is False:
                dep = self.create(modify_data)
            else:
                # change where the employee in the department status to active = False
                self.env['hr.employee'].search([('we_department_ids.we_id', '=', dep_detail['id'])]).write(
                    {'active': False})
                dep.write(modify_data)

            await self.env['hr.employee'].sync_user(dep, dep_detail['id'])

            if len(server_dep['children']) > 0:
                for child in server_dep['children']:
                    _tasks.append(_sync_dep(child, dep.id))
                await asyncio.gather(*_tasks)

        for department in depart_tree:
            tasks.append(_sync_dep(department, False))

        await asyncio.gather(*tasks)

    def on_we_create_party(self, xml_tree, company):
        """
        on wechat enterprise create department event, only has Id and ParentId, no Name or Other fields
        :param xml_tree: ET.fromstring(str) instance
        :param company: receive company
        :return:
        """
        we_id = xml_tree.find('Id').text
        we_parent_id = xml_tree.find('ParentId').text
        parent_dep = self.sudo().search([('we_id', '=', we_parent_id), ('company_id', '=', company.id)])
        self.sudo().create({
            'company_id': company.id,
            'name': f'we_id_{we_id}',
            'we_id': we_id,
            'parent_id': parent_dep.id,
            'we_parent_id': we_parent_id,
            'manager_id': False
        })
        return 'success'

    def on_we_update_party(self, xml_tree, company):
        """
        on wechat enterprise update department event, only has Id and ParentId, no Name or Other fields
        :param xml_tree: ET.fromstring(str) instance
        :param company: receive company
        :return:
        """
        we_id = xml_tree.find('Id').text
        we_parent_id = xml_tree.find('ParentId').text
        dep = self.sudo().search([('we_id', '=', we_id), ('company_id', '=', company.id)])
        if dep.id is not False:
            parent_dep = self.sudo().search([('we_id', '=', we_parent_id), ('company_id', '=', company.id)])
            dep.write({
                'parent_id': parent_dep.id,
                'we_parent_id': we_parent_id
            })
        return 'success'

    def on_we_delete_party(self, xml_tree, company):
        """
        on wechat enterprise delete department event, only has Id and ParentId, no Name or Other fields
        :param xml_tree: ET.fromstring(str) instance
        :param company: receive company
        :return:
        """
        we_id = xml_tree.find('Id').text
        dep = self.sudo().search([('we_id', '=', we_id), ('company_id', '=', company.id)])
        if dep.id is not False:
            dep.unlink()
        return 'success'
