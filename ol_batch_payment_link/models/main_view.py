import hashlib
import hmac

from werkzeug import urls

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError,UserError
from odoo.tools import ustr, consteq, float_compare
from odoo.addons.account.wizard.account_payment_register import AccountPaymentRegister as AV

class PaymentSchedule(models.Model):
    _inherit='account.payment'
    def schedule_payment(self):
        for rec in self.env['account.payment'].search([('payment_type','=','inbound')]):
            for inv in rec.reconciled_invoice_ids:
                try:
                    if inv.batch and inv.payment_state=='paid':
                        rec.action_draft()
                        rec.action_post()
                        for mi in inv.reference_invoices:
                            line_id=self.env['account.move.line'].search([('move_id','=',rec.move_id.id),('debit','=',0)])
                            mi.js_assign_outstanding_line(line_id.id)
                            inv.button_draft()
                            inv.button_cancel()
                except:
                    pass

class OlPaymentRegister(models.Model):
    _inherit = 'account.move'

    def action_create_payments(self):
        payments = self._create_payments()

        if self._context.get('dont_redirect_to_payments'):
            return True

        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })
        return action

    AV.action_register_payment = action_create_payments

class custompaymentWizard(models.Model):
    _name="ol.pay.wizard"

    res_model = fields.Char('Related Document Model', required=True)
    res_id = fields.Integer('Related Document ID', required=True)
    amount = fields.Monetary(currency_field='currency_id', required=True)
    amount_max = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one('res.currency')
    partner_id = fields.Many2one('res.partner')
    partner_email = fields.Char(related='partner_id.email')
    link = fields.Char(string='Payment Link', compute='_compute_values')
    description = fields.Char('Payment Ref')
    access_token = fields.Char(compute='_compute_values')
    company_id = fields.Many2one('res.company', compute='_compute_company')

    # @api.onchange('amount', 'description')
    # def _onchange_amount(self):
    #     if float_compare(self.amount_max, self.amount, precision_rounding=self.currency_id.rounding or 0.01) == -1:
    #         raise ValidationError(_("Please set an amount smaller than %s.") % (self.amount_max))
    #     if self.amount <= 0:
    #         raise ValidationError(_("The value of the payment amount must be positive."))


    @api.depends('amount', 'description', 'partner_id', 'currency_id')
    def _compute_values(self):
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        for payment_link in self:
            token_str = '%s%s%s' % (payment_link.partner_id.id, payment_link.amount, payment_link.currency_id.id)
            payment_link.access_token = hmac.new(secret.encode('utf-8'), token_str.encode('utf-8'), hashlib.sha256).hexdigest()
        # must be called after token generation, obvsly - the link needs an up-to-date token
        self._generate_link()

    @api.depends('res_model', 'res_id')
    def _compute_company(self):
        for link in self:
            record = self.env[link.res_model].browse(link.res_id)
            link.company_id = record.company_id if 'company_id' in record else False

    def _generate_link(self):
        for payment_link in self:
            record = self.env[payment_link.res_model].browse(payment_link.res_id)
            link = ('%s/website_payment/pay?reference=%s&amount=%s&currency_id=%s'
                    '&partner_id=%s&access_token=%s') % (
                        record.get_base_url(),
                        urls.url_quote_plus(payment_link.description),
                        payment_link.amount,
                        payment_link.currency_id.id,
                        payment_link.partner_id.id,
                        payment_link.access_token
                    )
            if payment_link.company_id:
                link += '&company_id=%s' % payment_link.company_id.id
            if payment_link.res_model == 'account.move':
                link += '&invoice_id=%s' % payment_link.res_id
            payment_link.link = link

    @api.model
    def check_token(self, access_token, partner_id, amount, currency_id):
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret')
        token_str = '%s%s%s' % (partner_id, amount, currency_id)
        correct_token = hmac.new(secret.encode('utf-8'), token_str.encode('utf-8'), hashlib.sha256).hexdigest()
        if consteq(ustr(access_token), correct_token):
            return True
        return False

class SaleOrderCrmOL(models.Model):
    _inherit = 'account.move'
    batch=fields.Boolean("Batch",default=False)
    # reference_invoices=fields.Many2many('account.move',string="Invoice References")
    reference_invoices = fields.Many2many(
            comodel_name='account.move',
            relation='contents_found_rel',
            column1='lot_id',
            column2='content_id',
            string='Invoice References')
    

    def generate_batch_link(self):
        active_ids = self.env.context.get('active_ids')
        sequence = self.env['ir.sequence'].search([('name','=','INV Sequence'),('company_id','=',self.env.company.id)])
        # next= sequence.get_next_char(sequence.number_next_actual)
        # while self.search([('name','=',next)]):
        #     sequence['number_next_actual']=sequence.number_next_actual+1
        #     next= sequence.get_next_char(sequence.number_next_actual)
        data={
        "invoice_line_ids":[],
        'move_type':'out_invoice',
        'batch':True,
        'reference_invoices':[(6,0,active_ids)],
        # 'name':next,
        'payment_reference':''
        }
        check_cond=True
        obj=self.env['account.move']
        wizard_form = self.env.ref('payment.payment_link_wizard_view_form', False)
        customer_check=obj.search([('id','=',active_ids[0])])
        for ai in active_ids:
            obj_inv=obj.search([('id','=',ai)])
            if obj_inv.state=="draft":
                check_cond=False
                raise UserError("You can only create batch payment for posted invoice")
            if customer_check.partner_id.id != obj_inv.partner_id.id:
                raise UserError("Customer should be same for batch payment")
            data['partner_id']=obj_inv.partner_id.id
            data['invoice_date']=obj_inv.invoice_date
            data['payment_reference']=data['payment_reference']+', '+obj_inv.name
            for il in obj_inv.invoice_line_ids:
                data["invoice_line_ids"].append((0,0,{
                'product_id':il.product_id.id,
                'quantity':il.quantity,
                'price_unit':il.price_unit,
                'tax_ids':[(6,0,il.tax_ids.ids)]
                }))
        if check_cond:
            created=obj.create(data)
            created.action_post()
            view = self.env.ref('ol_batch_payment_link.ol_payment_link_wizard_view_form')
            ctx = {
                'default_description':created.name,
                'default_res_id': created.id,
                "default_res_model":"account.move",
                "default_amount":created.amount_residual,
                "default_partner_id":created.partner_id.id,
                "default_amount_max":created.amount_residual,
                "default_currency_id":created.currency_id.id
            }
            res={
                    'name':"action.name",
                    'res_model': "ol.pay.wizard",
                    'type': "ir.actions.act_window",
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': view.id,
                    'target': 'new',
                    'context': ctx,
                }
            return res 