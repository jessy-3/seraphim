from django.http.response import HttpResponse
from django.core import serializers

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
from django.utils import timezone
import json
import datetime
import requests
from django.utils.dateparse import parse_datetime
#from django.db.models import Max, Min

from django.shortcuts import render
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import SymbolInfo, OhlcPrice, TslaPrice
from .wsclient import ws_client

msg = 'Hello from server!'
counter = 0

# simple serializer for student
class StudentForm(serializers.Serializer):
    name = serializers.CharField()
    address = serializers.CharField()

# simple endpoint to take the serializer data
class Student(APIView):
#    permission_classes = (permissions.AllowAny,)
#    @swagger_auto_schema(request_body=StudentForm)
    def post(self, request):
        serializer = StudentForm(data=request.data)
        if serializer.is_valid():
            json = serializer.data
            return Response(
                data={"status": "OK", "message": json},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OhlcSerializer(serializers.ModelSerializer):
    class Meta:
        model = OhlcPrice
        # fields = '__all__'
        fields = ['id', 'unix', 'date', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'volume_base', 'interval']

    def to_representation(self, instance):
        unixdatetime_field = instance.unix.timestamp()
        return {'id': instance.id,
            'unix': unixdatetime_field,
            'date':instance.date,
            'symbol':instance.symbol,
            'open':instance.open,
            'high':instance.high,
            'low':instance.low,
            'close':instance.close,
            'volume':instance.volume,
            'volume_base':instance.volume_base,
            'interval':instance.interval
        }

class TslaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TslaPrice
        fields = '__all__'

def symbol_config(symboluri):
    qs = SymbolInfo.objects.filter(trading="Enabled")
    cfg = { "symbol":"Invalid" }
    for instance in qs:
        if symboluri.lower() == instance.url_symbol:
            cfg = { "symbol" : instance.name }
    return cfg

class Ticker(APIView):
#    permission_classes = (permissions.AllowAny,)
#    @swagger_auto_schema(request_body=StudentForm)

    def get(self, request, symboluri):
        ticker_base = "https://www.bitstamp.net/api/v2/ticker/"
        symcfg = symbol_config(symboluri)
        # ws_client('start')
        # ws_client('subscribe','order_book_btcusd')
        if symcfg['symbol'] == "Invalid":
            return Response({
                'status': False,
                'message': "Ticker for " + symboluri + ' Not Supported'
            })

        print("checking price...")
        resp = requests.get(ticker_base + symboluri)
        if resp.status_code == 200:
            # minfo = f"Current { symcfg['symbol'] }: ${resp.json()['last']}. Change in last 24 hours: {resp.json()['percent_change_24']}%"
            respdata = resp.json()
            respdata['symbol'] = symcfg['symbol']
            respdata['date'] = datetime.datetime.fromtimestamp(int(respdata['timestamp']))
            return Response(respdata)
        return Response({
            'status': False,
            'message': 'Failed in obtaining ticker for ' + symcfg['symbol']
        })


class Ohlc(APIView):
#    permission_classes = (permissions.AllowAny,)
#    @swagger_auto_schema(request_body=StudentForm)

    def get(self, request, symboluri, pdt=None):
        # price_qset = OPrice.objects.all()
        symcfg = symbol_config(symboluri)
        # ws_client('stop')
        # ws_client('unsubscribe','order_book_btcusd')
        if symcfg['symbol'] == "Invalid":
            return Response({
                'status': False,
                'message': "Ohlc for " + symboluri + ' Not Supported'
            })

        try:
            if pdt:
                try:
                    qdate = parse_datetime(pdt)
                    print(qdate)
                    if (qdate is None):
                        raise ValueError('Not a valid date')
                except (ValueError, TypeError):
                    return Response({
                        'status': False,
                        'message': 'OHLC parameter ' + pdt + ' invalid.'
                    })
                if len(pdt)<11:
                    price_qset = OhlcPrice.objects.filter(symbol=symcfg['symbol'], interval=86400, date__year=qdate.year, date__month=qdate.month, date__day=qdate.day).order_by('-date')
                else:
                    price_qset = OhlcPrice.objects.filter(symbol=symcfg['symbol'], interval=3600, date__year=qdate.year, date__month=qdate.month, date__day=qdate.day, date__hour=qdate.hour).order_by('-date')
            else:
                price_qset = OhlcPrice.objects.filter(symbol=symcfg['symbol'], interval=86400).order_by('-date')[:1]
            # args = OhlcPrice.objects.filter(symbol=symcfg['symbol'], interval=86400)
            # lastdate = args.aggregate(Max('date'))['date__max']
            # price_qset = OhlcPrice.objects.filter(symbol=symcfg['symbol'], date=lastdate, interval=86400)
            # price_qset = OPrice.objects.filter(date__contains=datetime.date(2023,1,3) )
            # price_qset = OPrice.objects.filter(date__year=2023).order_by('date')
            # price_qset = OPrice.objects.filter(close__gt=65000).order_by('-close')
            # print(price_qset.last().details)
            # print(price_qset.count(),price_qset)
            if price_qset.count():
                # if symboluri.lower() == 'btcusd':
                ps = OhlcSerializer(price_qset, many=True)
                # else:
                #     ps = EthSerializer(price_qset, many=True)
                data = ps.data  # 序列化接口
                print(data)
                return Response(data)
            else:
                return Response({
                    'status': False,
                    'message': f'Not Found OHLC for {symboluri} on {pdt}'
                })
        except Exception:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            # return Response(status=status.HTTP_404_NOT_FOUND)


    # def post(self, request):
    #     serializer = Btc??Serializer(data=request.data)
    #     if serializer.is_valid():
    #         json = serializer.data
    #         return Response(
    #             data={"status": "OK", "message": json},
    #             status=status.HTTP_201_CREATED,
    #         )
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt # Tells Django not to worry about cross-site request forgery
# a view to fetch all todo items
def getResponse(request):
    if request.method == 'GET': # make sure the request is a GET request
        global counter
        counter = counter + 1
#        todos = TodoItem.objects.values() # query all todo items in our TodoItem model, we use the .values() because Queryset is not serializable
#        todos_list = list(todos) # list converts query sets to python readable list
        return JsonResponse({
            'status': True,
            'message': msg, # return a field `payload` containing an array of todo items
            'count' : counter
        }, safe=False) #
    # return false message if any other method is used
    return JsonResponse({
        'status': False,
        'message': 'ONLY GET METHOD ALLOWED'
    })

@csrf_exempt # Tells Django not to worry about cross-site request forgery
# add a todo item to our model
def setMessage(request):
    if request.method == 'POST': # make sure the request is a POST request
        # First we will read the todo data from the request.body object
        body = ''
        try:
            body = json.loads(request.body.decode('utf-8')) # parse JSON body from string to python dictionary
        except json.JSONDecodeError:
            return JsonResponse({
                'status': False,
                'message': 'JSON body was not supplied' # tell the developer to set the content type to application/json and pass and empty json
            })
        message = body.get('message')
        # next, check if the title is empty or null
        if message is None or message == '':
            # return false message if field `title` is empty or null
            return JsonResponse({
                'status': False,
                'message': 'Field `message` is required'
            })
#        todo = TodoItem(title=title, description=description) # Initialize a new Todo Item
#        todo.save() # save todo item
        global msg
        msg = message
        #return true message after saving the todo item
        return JsonResponse({
            'status': True,
            'message': f'message: {message}  has been updated'
        })
    # return false message if any other method is used
    return JsonResponse({
        'status': False,
        'message': 'ONLY POST METHOD ALLOWED'
    })


@csrf_exempt # Tells Django not to worry about cross-site request forgery
# add a todo item to our model
def setCounter(request):
    if request.method == 'POST': # make sure the request is a POST request
        # First we will read the todo data from the request.body object
        body = ''
        try:
            body = json.loads(request.body.decode('utf-8')) # parse JSON body from string to python dictionary
        except json.JSONDecodeError:
            return JsonResponse({
                'status': False,
                'counter': 'JSON body was not supplied' # tell the developer to set the content type to application/json and pass and empty json
            })
        count = body.get('counter')
        # next, check if the title is empty or null
        if count is None or count == '':
            # return false message if field `title` is empty or null
            return JsonResponse({
                'status': False,
                'counter': 'Field `counter` is required'
            })
#        todo = TodoItem(title=title, description=description) # Initialize a new Todo Item
#        todo.save() # save todo item
        global counter
        counter = count
        #return true message after saving the todo item
        return JsonResponse({
            'status': True,
            'counter': f'counter: {count}  has been updated'
        })
    # return false message if any other method is used
    return JsonResponse({
        'status': False,
        'message': 'ONLY POST METHOD ALLOWED'
    })
