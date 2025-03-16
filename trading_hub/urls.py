from django.urls import path
from . import views

urlpatterns = [
    path('', views.trade_list, name='trade_list'),
    path('create/', views.create_trade, name='create_trade'),
    path('trade/<int:trade_id>/complete/', views.complete_trade, name='complete_trade'),
    path('trader/<str:username>/', views.trader_profile, name='trader_profile'),
    path('traders/top/', views.top_traders, name='top_traders'),
]
