from odoo import http
from odoo.http import request
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager

class CustomCustomerPortal(CustomerPortal):

    def _prepare_sale_portal_rendering_values(self, page=1, date_begin=None, date_end=None, sortby=None, quotation_page=False, **kwargs):
        # Let parent handle basic values, but we might overwrite orders if it's the orders page
        values = super()._prepare_sale_portal_rendering_values(
            page=page, date_begin=date_begin, date_end=date_end, sortby=sortby, quotation_page=quotation_page, **kwargs
        )

        if not quotation_page:
            # Re-calculate orders with our custom tab logic
            SaleOrder = request.env['sale.order']
            partner = request.env.user.partner_id
            
            # Base domain for the user
            base_domain = [('partner_id', 'child_of', [partner.commercial_partner_id.id])]
            
            tab = kwargs.get('tab', 'all')
            if tab == 'to_pay':
                domain = base_domain + [('state', 'in', ['draft', 'sent'])]
            elif tab == 'to_ship':
                # sale state and not fully delivered
                domain = base_domain + [('state', '=', 'sale'), ('delivery_status', 'in', ['pending', 'partial'])]
            elif tab == 'to_receive':
                # sale/done state and fully delivered, but not yet confirmed received by customer
                domain = base_domain + [('state', 'in', ['sale', 'done']), ('delivery_status', '=', 'full'), ('customer_received', '=', False)]
            elif tab == 'completed':
                # Customer has confirmed receipt
                domain = base_domain + [('customer_received', '=', True)]
            elif tab == 'cancelled':
                domain = base_domain + [('state', '=', 'cancel')]
            else:
                # 'all' includes draft, sent, sale, done, cancel
                domain = base_domain
            
            # Additional date filters
            if date_begin and date_end:
                domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
                
            searchbar_sortings = self._get_sale_searchbar_sortings()
            sortby = sortby if sortby else 'date'
            sort_order = searchbar_sortings.get(sortby, searchbar_sortings['date'])['order']
            
            url_args = {'date_begin': date_begin, 'date_end': date_end, 'tab': tab}
            if len(searchbar_sortings) > 1:
                url_args['sortby'] = sortby

            # Total counts for tabs (badges)
            tab_counts = {
                'all': SaleOrder.search_count(base_domain) if SaleOrder.has_access('read') else 0,
                'to_pay': SaleOrder.search_count(base_domain + [('state', 'in', ['draft', 'sent'])]) if SaleOrder.has_access('read') else 0,
                'to_ship': SaleOrder.search_count(base_domain + [('state', '=', 'sale'), ('delivery_status', 'in', ['pending', 'partial'])]) if SaleOrder.has_access('read') else 0,
                'to_receive': SaleOrder.search_count(base_domain + [('state', 'in', ['sale', 'done']), ('delivery_status', '=', 'full'), ('customer_received', '=', False)]) if SaleOrder.has_access('read') else 0,
                'completed': SaleOrder.search_count(base_domain + [('customer_received', '=', True)]) if SaleOrder.has_access('read') else 0,
                'cancelled': SaleOrder.search_count(base_domain + [('state', '=', 'cancel')]) if SaleOrder.has_access('read') else 0,
            }

            pager_values = portal_pager(
                url="/my/orders",
                total=tab_counts.get(tab, tab_counts['all']),
                page=page,
                step=self._items_per_page,
                url_args=url_args,
            )

            orders = SaleOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager_values['offset']) if SaleOrder.has_access('read') else SaleOrder

            values.update({
                'orders': orders,
                'pager': pager_values,
                'current_tab': tab,
                'tab_counts': tab_counts,
            })

        return values

    @http.route(['/my/orders/receive/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_orders_receive(self, order_id=None, **kw):
        """Mark order as received by customer."""
        try:
            order_sudo = self._document_check_access('sale.order', order_id)
        except Exception:
            return request.redirect('/my/orders')
            
        if order_sudo and order_sudo.delivery_status == 'full' and not order_sudo.customer_received:
            order_sudo.sudo().write({'customer_received': True})
            
        return request.redirect('/my/orders?tab=completed')
