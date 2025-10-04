from django.contrib import admin

# Register your models here.
from . models import SymbolInfo, OhlcPrice, TslaPrice

class SymbolAdmin(admin.ModelAdmin):
    list_display = ('name', 'url_symbol', 'base_decimals', 'counter_decimals', 'trading', 'description')

class OhlcAdmin(admin.ModelAdmin):
    list_display = ('date', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'volume_base', 'interval')

admin.site.register(SymbolInfo, SymbolAdmin)
admin.site.register(OhlcPrice, OhlcAdmin)
admin.site.register(TslaPrice, OhlcAdmin)
