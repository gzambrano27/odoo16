{
    'name': "Advance Reordering",
    'author': "INKERP",
    'website': "www.inkerp.com",
    "summary": "This app will predict future requirement of stock quantity in advance based on past sold stock quantity.  stock report, advance report, advance stock report, ai inventory, ai stock ,Advance Reordering, Purchase Reorder,Inventory Management ,Stock Planner,Inventory Scheduler,Supply Forecasting,Stock Optimization,Inventory Planning Tool,Demand Forecasting,Inventory Forecasting,Stock Control,Inventory StrategyIt helps to manage customer demand with the right level of inventory by placing Purchase Order or replenishing inventories using inter company or inter warehouse, inventory management technique, inventory coverage ratio, Advance reorder, order points, reordering rule, advance purchase ordering, sales forecast, inter company transfer, inter warehouse transfer, stock replenishment, demand, inventory, advance inventory,out of stock, over stock, order point, supply chain management, accurate inventory ",
    'Description':"""
    The Inventory Planner app streamlines stock management by predicting future inventory needs based on past sales data. Key features include:

    Automated Stock Prediction: Predict future stock requirements with advanced analytics.
    Customizable Stock Alerts: Set alerts for products nearing stockouts with color-coded priority indicators.
    Advanced Vendor Selection: Choose vendors manually or automatically based on delivery speed or cost.
    Tailored Inventory Planning: Configure stock prediction by adjusting extra stock days, lead times, growth multipliers, product categories, and warehouses.
    Color-Coded Stock Insights: Highlight stock status using intuitive yellow, red, and grey indicators.
    Comprehensive Reporting: Generate detailed inventory, sales, and purchase reports with profit and cost analysis.
    Manager Approval Workflow: Ensure purchase orders undergo a seamless approval process.
    Automatic Plan Generation: Automate inventory plan creation and purchase orders for optimal efficiency.
    note:From now on, you don’t need to add it in before app.

    """,
    'version': '16.0.2.0.0',
    'depends': ['sale_management', 'sale', 'purchase', 'stock'],
    'data': [
        'security/access_rights.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/inv_plan.xml',
        'views/inv_plan_tmpl_view.xml',
        'views/inv_plan_line_view.xml',
        'views/res_config_settings_view.xml',
        'views/product_template_view.xml',
        'views/product_sub_category.xml',
        'views/purchase_order_view.xml',
        'views/res_partner.xml',
        'report/sale_history_report.xml',
        'report/purchase_history_report.xml',
    ],
    'images': ['static/description/banner.gif'],
    'license': "OPL-1",
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': '50',
    'currency': 'EUR',
}
