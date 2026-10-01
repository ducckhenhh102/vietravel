import re

with open('core/wagtail_hooks.py', 'r', encoding='utf-8') as f:
    hooks = f.read()

with open('core/models.py', 'r', encoding='utf-8') as f:
    models = f.read()

# Copy STATUS_COLORS and render_status_badge
if "STATUS_COLORS =" not in models:
    badge_match = re.search(r'(# Mapping trạng thái → màu badge.*?def render_status_badge.*?    \))', hooks, re.DOTALL)
    if badge_match:
        models = models.replace(
            '# ===========================================================================\n# PHÂN HỆ CMS',
            'from django.utils.html import format_html\n\n' + badge_match.group(1) + '\n\n# ===========================================================================\n# PHÂN HỆ CMS'
        )

# Methods mapping
methods_to_move = {
    'Customer': ['get_full_name', 'get_email', 'membership_tier_badge', 'total_spent_fmt'],
    'TourProduct': ['get_tour_name', 'base_price_fmt', 'child_price_fmt', 'product_status_badge', 'get_departure_count'],
    'TourDeparture': ['get_tour_name', 'seats_display', 'effective_price_fmt', 'departure_status_badge'],
    'Booking': ['get_customer_name', 'get_tour_name', 'get_departure_date', 'num_passengers_fmt', 'final_amount_fmt', 'booking_status_badge', 'get_payment_status'],
    'Payment': ['get_transaction_id', 'get_booking_code', 'get_customer_name', 'amount_fmt', 'method_badge', 'payment_status_badge']
}

for model_name, methods in methods_to_move.items():
    for method in methods:
        pattern = r'(    def ' + method + r'\(self, obj: ' + model_name + r'\) -> str:.*?    ' + method + r'\.short_description = "[^"]+"(?:\n    ' + method + r'\.admin_order_field = "[^"]+")?)'
        match = re.search(pattern, hooks, re.DOTALL)
        if match:
            code = match.group(1)
            # Remove from hooks
            hooks = hooks.replace(code + '\n\n', '')
            hooks = hooks.replace(code + '\n', '')
            hooks = hooks.replace(code, '')
            
            # Prepare code for model
            code = code.replace(f'self, obj: {model_name}', 'self')
            code = code.replace('obj.', 'self.')
            # Change `method.short_description = ...` to `def method(self): ...` (wait, properties don't need this, but for Wagtail list_display, normal methods are fine. The short_description is set on the method).
            # It's already in the code block!
            
            # Insert into models.py
            # Find the end of the class by looking for the next class or end of file
            class_idx = models.find(f'class {model_name}(models.Model):')
            if class_idx != -1:
                next_class_idx = models.find('\nclass ', class_idx + 1)
                if next_class_idx == -1:
                    next_class_idx = len(models)
                
                # Insert right before next_class_idx
                insertion = '\n' + code + '\n'
                models = models[:next_class_idx] + insertion + models[next_class_idx:]

with open('core/wagtail_hooks.py', 'w', encoding='utf-8') as f:
    f.write(hooks)

with open('core/models.py', 'w', encoding='utf-8') as f:
    f.write(models)

print("Done patching.")
