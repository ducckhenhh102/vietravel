with open('core/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. base_price_fmt
content = content.replace(
'''    def base_price_fmt(self) -> str:
        return format_html(
            "<strong>{:,.0f}</strong> đ",
            self.base_price,
        )''',
'''    def base_price_fmt(self) -> str:
        return format_html(
            "<strong>{}</strong> đ",
            f"{self.base_price:,.0f}" if self.base_price else "0",
        )'''
)

# 2. child_price_fmt
content = content.replace(
'''    def child_price_fmt(self) -> str:
        if self.child_price:
            return format_html("<em>{:,.0f}</em> đ", self.child_price)
        return format_html('<span style="color:#aaa">—</span>')''',
'''    def child_price_fmt(self) -> str:
        if self.child_price:
            return format_html("<em>{}</em> đ", f"{self.child_price:,.0f}")
        return format_html('<span style="color:#aaa">—</span>')'''
)

# 3. effective_price_fmt
content = content.replace(
'''    def effective_price_fmt(self) -> str:
        price = self.effective_price
        if self.price_override:
            return format_html(
                '<span style="color:#f59e0b;font-weight:600">'
                "{:,.0f} đ ✦</span>",
                price,
            )
        return format_html("{:,.0f} đ", price)''',
'''    def effective_price_fmt(self) -> str:
        price = self.effective_price
        if self.price_override:
            return format_html(
                '<span style="color:#f59e0b;font-weight:600">'
                "{} đ ✦</span>",
                f"{price:,.0f}" if price else "0",
            )
        return format_html("{} đ", f"{price:,.0f}" if price else "0")'''
)

# 4. total_spent_fmt
content = content.replace(
'''    def total_spent_fmt(self) -> str:
        return format_html(
            "<strong>{:,.0f}</strong> <small>VNĐ</small>",
            self.total_spent,
        )''',
'''    def total_spent_fmt(self) -> str:
        return format_html(
            "<strong>{}</strong> <small>VNĐ</small>",
            f"{self.total_spent:,.0f}" if self.total_spent else "0",
        )'''
)

# 5. final_amount_fmt
content = content.replace(
'''    def final_amount_fmt(self) -> str:
        return format_html(
            '<strong style="color:#059669">{:,.0f}</strong> đ',
            self.final_amount,
        )''',
'''    def final_amount_fmt(self) -> str:
        return format_html(
            '<strong style="color:#059669">{}</strong> đ',
            f"{self.final_amount:,.0f}" if self.final_amount else "0",
        )'''
)

# 6. amount_fmt
content = content.replace(
'''    def amount_fmt(self) -> str:
        return format_html(
            '<strong style="color:#059669">{:,.0f}</strong> đ',
            self.amount,
        )''',
'''    def amount_fmt(self) -> str:
        return format_html(
            '<strong style="color:#059669">{}</strong> đ',
            f"{self.amount:,.0f}" if self.amount else "0",
        )'''
)

with open('core/models.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Formatting fixed!")
