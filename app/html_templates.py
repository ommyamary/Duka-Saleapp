def generate_receipt_html(transaction, company, customer=None) -> str:
    # Enhanced HTML receipt with conditional field display
    items_html = ""
    for item in transaction.items:
        qty = item.get("quantity", 1)
        price = item.get("unitPrice", item.get("price", item.get("selling_price", 0)))
        total = qty * price
        items_html += f"""
        <div class="item-row">
            <div class="item-name">{item.get('name', item.get('productName', 'Item'))}</div>
            <div class="item-details">{qty} x {price:,.2f}</div>
            <div class="item-total">{total:,.2f}</div>
        </div>
        """

    company_name = company.name if company else "Duka Lako"
    
    # Build company details section with conditional display
    company_details = []
    if company.physical_address or company.address:
        company_details.append(company.physical_address or company.address)
    if company.phone:
        company_details.append(f"Tel: {company.phone}")
    if company.email:
        company_details.append(f"Email: {company.email}")
    if company.website:
        company_details.append(f"Website: {company.website}")
    if company.vrn_no:
        company_details.append(f"VRN No: {company.vrn_no}")
    if company.tin_no:
        company_details.append(f"TIN No: {company.tin_no}")

    company_details_html = ""
    for detail in company_details:
        company_details_html += f"<p>{detail}</p>"

    # Build customer details section with conditional display
    customer_details = []
    if customer:
        if customer.business_name and customer.business_name != customer.name:
            customer_details.append(f"<strong>Customer:</strong> {customer.business_name}")
            if customer.contact_person:
                customer_details.append(f"Attn: {customer.contact_person}")
        else:
            customer_details.append(f"<strong>Customer:</strong> {customer.name}")
        
        if customer.customer_number:
            customer_details.append(f"Customer No: {customer.customer_number}")
        if customer.phone:
            customer_details.append(f"Tel: {customer.phone}")
        if customer.email:
            customer_details.append(f"Email: {customer.email}")
        if customer.vrn_no:
            customer_details.append(f"VRN No: {customer.vrn_no}")
        if customer.tin_no:
            customer_details.append(f"TIN No: {customer.tin_no}")
        if customer.physical_address or customer.address:
            customer_details.append(f"Address: {customer.physical_address or customer.address}")
    elif transaction.customer_name:
        customer_details.append(f"<strong>Customer:</strong> {transaction.customer_name}")

    customer_details_html = ""
    for detail in customer_details:
        customer_details_html += f"<p>{detail}</p>"

    html = f"""
    <!DOCTYPE html>
    <html lang="sw">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Receipt - {transaction.transaction_number}</title>
        <style>
            body {{
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f1f5f9;
                color: #333;
            }}
            .receipt-container {{
                max-width: 500px;
                margin: 0 auto;
                background: #fff;
                padding: 30px 20px;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            }}
            .header {{
                text-align: center;
                margin-bottom: 20px;
                border-bottom: 2px solid #25A18E;
                padding-bottom: 20px;
            }}
            .header h1 {{
                margin: 0 0 10px 0;
                color: #25A18E;
                font-size: 24px;
                font-weight: bold;
            }}
            .header p {{
                margin: 2px 0;
                font-size: 12px;
                color: #666;
            }}
            .company-details, .customer-details {{
                margin-bottom: 20px;
                font-size: 12px;
                color: #555;
                background: #f8fafc;
                padding: 15px;
                border-radius: 6px;
            }}
            .transaction-details {{
                margin-bottom: 20px;
                font-size: 12px;
                color: #555;
            }}
            .items-table {{
                width: 100%;
                border-bottom: 2px solid #eee;
                margin-bottom: 20px;
                padding-bottom: 10px;
            }}
            .item-row {{
                display: flex;
                flex-wrap: wrap;
                margin-bottom: 10px;
            }}
            .item-name {{
                flex: 1 1 100%;
                font-weight: bold;
                margin-bottom: 4px;
            }}
            .item-details {{
                flex: 1;
                color: #666;
                font-size: 12px;
            }}
            .item-total {{
                flex: 0 0 100px;
                text-align: right;
                font-weight: bold;
            }}
            .totals-row {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
                font-size: 14px;
            }}
            .grand-total {{
                font-size: 18px;
                font-weight: bold;
                color: #FF6B2C;
                border-top: 2px solid #eee;
                padding-top: 10px;
                margin-top: 5px;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                font-size: 12px;
                color: #888;
                border-top: 1px solid #eee;
                padding-top: 20px;
            }}
            .company-logo {{
                max-width: 100px;
                max-height: 60px;
                margin-bottom: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="receipt-container">
            <div class="header">
                {f'<img src="{company.logo}" alt="Logo" class="company-logo">' if company and company.logo else ''}
                <h1>{company_name}</h1>
                {company_details_html}
            </div>
            
            {f'<div class="customer-details">{customer_details_html}</div>' if customer_details_html else ''}
            
            <div class="transaction-details">
                <p><strong>Receipt Number:</strong> {transaction.transaction_number}</p>
                <p><strong>Date:</strong> {transaction.created_at.strftime('%d-%m-%Y %H:%M')}</p>
                <p><strong>Sales Person:</strong> {transaction.cashier_name or 'Cashier'}</p>
                <p><strong>Payment Method:</strong> {transaction.payment_method.title()}</p>
            </div>
            
            <div class="items-table">
                <h3 style="margin-bottom: 15px; color: #25A18E;">Items</h3>
                {items_html}
            </div>
            
            <div class="totals-section">
                {(transaction.discount_amount or 0) > 0 and f'''
                <div class="totals-row">
                    <span>Subtotal</span>
                    <span>{company.currency_symbol if company else 'TSh'}{transaction.subtotal:,.2f}</span>
                </div>
                <div class="totals-row">
                    <span>Discount</span>
                    <span style="color: #dc2626;">-{company.currency_symbol if company else 'TSh'}{transaction.discount_amount:,.2f}</span>
                </div>
                ''' or ''}
                {(transaction.tax_amount or 0) > 0 and f'''
                <div class="totals-row">
                    <span>Tax</span>
                    <span>{company.currency_symbol if company else 'TSh'}{transaction.tax_amount:,.2f}</span>
                </div>
                ''' or ''}
                <div class="totals-row grand-total">
                    <span>Total</span>
                    <span>{company.currency_symbol if company else 'TSh'}{transaction.total:,.2f}</span>
                </div>
                <div class="totals-row">
                    <span>Amount Paid</span>
                    <span>{company.currency_symbol if company else 'TSh'}{transaction.amount_paid:,.2f}</span>
                </div>
                {transaction.amount_due > 0 and f'''
                <div class="totals-row" style="color: #d32f2f;">
                    <span>Amount Due</span>
                    <span>{company.currency_symbol if company else 'TSh'}{transaction.amount_due:,.2f}</span>
                </div>
                ''' or ''}
                {transaction.change and transaction.change > 0 and f'''
                <div class="totals-row" style="color: #16a34a;">
                    <span>Change</span>
                    <span>{company.currency_symbol if company else 'TSh'}{transaction.change:,.2f}</span>
                </div>
                ''' or ''}
            </div>
            
            {company.document_footer and f'<div style="margin-top: 20px; padding: 15px; background: #f1f5f9; border-radius: 6px; font-size: 11px; color: #666; text-align: center;">{company.document_footer}</div>' or ''}
            
            <div class="footer">
                <p>Thank you for your business!</p>
                <p style="font-size: 10px; margin-top: 10px; color: #aaa;">Powered by DUKA-SALES</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def generate_invoice_html(transaction, company, customer=None, terms_conditions=None) -> str:
    # Professional invoice template with conditional fields
    items_html = ""
    for item in transaction.items:
        qty = item.get("quantity", 1)
        price = item.get("unitPrice", item.get("price", 0))
        total = qty * price
        items_html += f"""
        <tr>
            <td>{item.get('name', 'Item')}</td>
            <td>{qty}</td>
            <td>{company.currency_symbol if company else 'TSh'}{price:,.2f}</td>
            <td>{company.currency_symbol if company else 'TSh'}{total:,.2f}</td>
        </tr>
        """

    # Build company details
    company_details = []
    if company.physical_address or company.address:
        company_details.append(company.physical_address or company.address)
    if company.phone:
        company_details.append(f"Tel: {company.phone}")
    if company.email:
        company_details.append(f"Email: {company.email}")
    if company.website:
        company_details.append(f"Website: {company.website}")
    if company.vrn_no:
        company_details.append(f"VRN No: {company.vrn_no}")
    if company.tin_no:
        company_details.append(f"TIN No: {company.tin_no}")

    # Build customer and shipping details
    customer_details = []
    shipping_details = []
    
    if customer:
        if customer.business_name and customer.business_name != customer.name:
            customer_details.append(f"<strong>Customer:</strong> {customer.business_name}")
            if customer.contact_person:
                customer_details.append(f"Attn: {customer.contact_person}")
        else:
            customer_details.append(f"<strong>Customer:</strong> {customer.name}")
        
        if customer.customer_number:
            customer_details.append(f"Customer No: {customer.customer_number}")
        if customer.phone:
            customer_details.append(f"Tel: {customer.phone}")
        if customer.email:
            customer_details.append(f"Email: {customer.email}")
        if customer.vrn_no:
            customer_details.append(f"VRN No: {customer.vrn_no}")
        if customer.tin_no:
            customer_details.append(f"TIN No: {customer.tin_no}")
        if customer.physical_address or customer.address:
            customer_details.append(f"Address: {customer.physical_address or customer.address}")
        
        # Shipping details
        if customer.shipping_address or (customer.physical_address or customer.address):
            shipping_details.append(f"<strong>Ship To:</strong>")
            shipping_details.append(customer.shipping_address or customer.physical_address or customer.address)
            if customer.shipping_city or customer.city:
                shipping_details.append(f"{customer.shipping_city or customer.city}, {customer.shipping_region or customer.region}")
            if customer.shipping_country or customer.country:
                shipping_details.append(customer.shipping_country or customer.country)

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Invoice - {transaction.transaction_number}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
            .invoice-container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border: 1px solid #ddd; }}
            .header {{ display: flex; justify-content: space-between; margin-bottom: 30px; border-bottom: 2px solid #333; padding-bottom: 20px; }}
            .company-details {{ flex: 1; }}
            .invoice-details {{ text-align: right; }}
            .customer-shipping {{ display: flex; gap: 40px; margin-bottom: 30px; }}
            .customer-info, .shipping-info {{ flex: 1; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f8f9fa; font-weight: bold; }}
            .totals {{ text-align: right; margin-top: 20px; }}
            .totals-row {{ display: flex; justify-content: flex-end; margin-bottom: 10px; }}
            .totals-label {{ width: 150px; text-align: right; padding-right: 20px; }}
            .totals-value {{ width: 120px; text-align: right; font-weight: bold; }}
            .grand-total {{ font-size: 18px; color: #2563eb; border-top: 2px solid #333; padding-top: 10px; }}
            .bank-details-section {{ margin-top: 30px; display: flex; gap: 20px; }}
            .bank-column {{ flex: 1; font-size: 12px; }}
            .bank-label {{ font-weight: bold; width: 100px; display: inline-block; }}
            .bank-value {{ display: inline-block; }}
            .signatory-section {{ margin-top: 40px; display: flex; justify-content: space-between; align-items: flex-end; }}
            .signatory-line {{ border-top: 1px solid #333; width: 250px; text-align: center; padding-top: 5px; font-size: 12px; }}
            .terms-conditions {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; }}
            .company-logo {{ max-width: 150px; max-height: 80px; margin-bottom: 10px; }}
        </style>
    </head>
    <body>
        <div class="invoice-container">
            <div class="header">
                <div class="company-details">
                    {f'<img src="{company.logo}" alt="Logo" class="company-logo">' if company and company.logo else ''}
                    <h2 style="margin: 0;">{company.name if company else 'Company'}</h2>
                    {chr(10).join([f'<p style="margin: 2px 0; font-size: 12px;">{detail}</p>' for detail in company_details])}
                </div>
                <div class="invoice-details">
                    <h1 style="margin: 0; color: #2563eb;">INVOICE</h1>
                    <p style="margin: 5px 0;"><strong>Invoice No:</strong> {transaction.transaction_number}</p>
                    <p style="margin: 5px 0;"><strong>Date:</strong> {transaction.created_at.strftime('%d-%m-%Y')}</p>
                    <p style="margin: 5px 0;"><strong>Due Date:</strong> {(transaction.created_at.replace(day=transaction.created_at.day + 30) if hasattr(transaction.created_at, 'day') else '30 days')}</p>
                </div>
            </div>
            
            <div class="customer-shipping">
                <div class="customer-info">
                    {chr(10).join([f'<p style="margin: 2px 0; font-size: 12px;">{detail}</p>' for detail in customer_details])}
                </div>
                {shipping_details and f'''
                <div class="shipping-info">
                    {chr(10).join([f'<p style="margin: 2px 0; font-size: 12px;">{detail}</p>' for detail in shipping_details])}
                </div>
                ''' or ''}
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Description</th>
                        <th>Quantity</th>
                        <th>Unit Price</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>
            
            <div class="totals">
                {(transaction.discount_amount or 0) > 0 and f'''
                <div class="totals-row">
                    <div class="totals-label">Subtotal:</div>
                    <div class="totals-value">{company.currency_symbol if company else 'TSh'}{transaction.subtotal:,.2f}</div>
                </div>
                <div class="totals-row">
                    <div class="totals-label">Discount:</div>
                    <div class="totals-value" style="color: #dc2626;">-{company.currency_symbol if company else 'TSh'}{transaction.discount_amount:,.2f}</div>
                </div>
                ''' or ''}
                {(transaction.tax_amount or 0) > 0 and f'''
                <div class="totals-row">
                    <div class="totals-label">Tax:</div>
                    <div class="totals-value">{company.currency_symbol if company else 'TSh'}{transaction.tax_amount:,.2f}</div>
                </div>
                ''' or ''}
                <div class="totals-row grand-total">
                    <div class="totals-label">Total:</div>
                    <div class="totals-value">{company.currency_symbol if company else 'TSh'}{transaction.total:,.2f}</div>
                </div>
            </div>

            {f'''
            <div class="bank-details-section">
                <div style="width: 100px; font-weight: bold; font-size: 14px;">Bank Details</div>
                {''.join([f"""
                <div class="bank-column">
                    <div style="margin-bottom: 5px;"><span class="bank-label">Bank</span><span class="bank-value">{bank.bank_name}</span></div>
                    <div style="margin-bottom: 5px;"><span class="bank-label">Branch name</span><span class="bank-value">{bank.branch_name or 'N/A'}</span></div>
                    <div style="margin-bottom: 5px;"><span class="bank-label">Acc. No:</span><span class="bank-value">{bank.account_number}</span></div>
                    {f'<div style="margin-bottom: 5px;"><span class="bank-label">Swift Code</span><span class="bank-value">{bank.swift_code}</span></div>' if bank.swift_code else ''}
                    {f'<div style="margin-bottom: 5px;"><span class="bank-label">Mobile Money</span><span class="bank-value">{bank.mobile_money_name}: {bank.mobile_money_number}</span></div>' if bank.mobile_money_number else ''}
                </div>
                """ for bank in company.bank_details if bank.is_active])}
            </div>
            ''' if any(b.is_active for b in company.bank_details) else ''}

            <div class="signatory-section">
                <div>
                    <p style="font-size: 12px; margin-bottom: 40px;">Acceptance of Invoice:</p>
                    <div class="signatory-line">
                        <strong>Name of Authorised Signatory</strong>
                        <p style="margin: 5px 0; font-size: 11px; color: #666;">{company.authorised_signatory or '_______________________'}</p>
                    </div>
                </div>
                <div class="signatory-line" style="width: 200px;">
                    <strong>Signature</strong>
                </div>
            </div>
            
            {terms_conditions and f'''
            <div class="terms-conditions">
                <h3>Terms & Conditions</h3>
                {terms_conditions.payment_terms and f'<p><strong>Payment Terms:</strong> {terms_conditions.payment_terms}</p>'}
                {terms_conditions.delivery_terms and f'<p><strong>Delivery Terms:</strong> {terms_conditions.delivery_terms}</p>'}
                {terms_conditions.terms_text and f'<p>{terms_conditions.terms_text}</p>'}
            </div>
            ''' or company.document_footer and f'''
            <div class="terms-conditions">
                <p style="font-size: 12px; color: #666;">{company.document_footer}</p>
            </div>
            ''' or ''}
            
            <div style="margin-top: 30px; text-align: center; font-size: 10px; color: #999;">
                Powered by DUKA-SALES
            </div>
        </div>
    </body>
    </html>
    """
    return html

def generate_statement_html(customer, company, debts) -> str:
    # A simple, mobile-friendly HTML statement
    debts_html = ""
    for debt in debts:
        debts_html += f"""
        <div class="debt-card">
            <div class="debt-header">
                <span class="debt-ref">{debt.reference_number}</span>
                <span class="debt-date">{debt.created_at.strftime('%d-%m-%Y')}</span>
            </div>
            <div class="debt-amounts">
                <span>Deni Asili: Tsh {debt.original_amount:,.0f}</span>
                <span class="debt-remaining">Bado: Tsh {debt.remaining_amount:,.0f}</span>
            </div>
        </div>
        """

    company_name = company.name if company else "Duka Lako"
    company_phone = company.phone if company else ""

    html = f"""
    <!DOCTYPE html>
    <html lang="sw">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mchanganuo wa Deni - {customer.name}</title>
        <style>
            body {{
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f1f5f9;
                color: #333;
            }}
            .statement-container {{
                max-width: 500px;
                margin: 0 auto;
                background: #fff;
                padding: 30px 20px;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            }}
            .header {{
                text-align: center;
                margin-bottom: 20px;
                padding-bottom: 20px;
                border-bottom: 2px solid #25A18E;
            }}
            .header h1 {{
                margin: 0 0 10px 0;
                color: #25A18E;
                font-size: 24px;
            }}
            .customer-info {{
                background: #f8fafc;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
            }}
            .customer-info h2 {{
                margin: 0 0 5px 0;
                font-size: 18px;
                color: #333;
            }}
            .summary-box {{
                background: #FF6B2C;
                color: #fff;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                margin-bottom: 25px;
            }}
            .summary-box p {{
                margin: 0;
                font-size: 14px;
                opacity: 0.9;
            }}
            .summary-box h3 {{
                margin: 10px 0 0 0;
                font-size: 32px;
            }}
            .debt-card {{
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 15px;
            }}
            .debt-header {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
                font-weight: bold;
                color: #475569;
            }}
            .debt-date {{
                color: #94a3b8;
                font-weight: normal;
                font-size: 14px;
            }}
            .debt-amounts {{
                display: flex;
                justify-content: space-between;
                font-size: 15px;
            }}
            .debt-remaining {{
                font-weight: bold;
                color: #e11d48;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                font-size: 14px;
                color: #888;
            }}
            .pay-btn {{
                display: block;
                width: 100%;
                padding: 15px;
                background-color: #25A18E;
                color: #fff;
                text-align: center;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
                margin-top: 20px;
                box-sizing: border-box;
            }}
        </style>
    </head>
    <body>
        <div class="statement-container">
            <div class="header">
                <h1>{company_name}</h1>
                <p>Mchanganuo wa Deni</p>
            </div>
            
            <div class="customer-info">
                <h2>Mteja: {customer.name}</h2>
                {f'<p style="margin:0; color:#666;">Simu: {customer.phone}</p>' if customer.phone else ''}
            </div>
            
            <div class="summary-box">
                <p>Jumla ya Deni Unalodaiwa</p>
                <h3>Tsh {customer.current_debt:,.0f}</h3>
            </div>
            
            <h3 style="color: #475569; margin-bottom: 15px;">Mchanganuo:</h3>
            
            {debts_html if debts_html else '<p style="text-align:center; color:#94a3b8;">Hakuna madeni yaliyosalia.</p>'}
            
            {f'<a href="https://wa.me/{company_phone.replace("+", "")}" class="pay-btn">Wasiliana Nasi Kulipa</a>' if company_phone else ''}
            
            <div class="footer">
                <p style="font-size: 11px; margin-top: 15px; color: #aaa;">Powered by DUKA-SALES</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html
