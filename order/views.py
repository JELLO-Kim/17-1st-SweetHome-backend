import json

from django.http      import JsonResponse
from django.views     import View
from django.db.models import Q
from django.db.utils  import DataError

from user.models    import User
from utils     import login_decorator
from order.models   import Order, OrderStatus, OrderProduct
from product.models import Product

class OrderProductView(View):
    @login_decorator
    def get(self, request):
        """ [Order] 장바구니 목록
        Args:
            - user: 회원 유효성 검사를 통해 token으로 부터 user 정보를 받는다.
        Returns: 
            - result : 로그인 user의 장바구니 목록 반환
        """
        try:
            user = request.user
            # 장바구니 목록을 반환하는데 상품이 없을 경우 (에러상황은 아니므로 status=200)
            if not Order.objects.filter(Q(user=user)&Q(status=1)).exists():
                return JsonResponse({'message':'장바구니에 담긴 상품 없음'}, status=200)

            order           = Order.objects.get(Q(user=user)&Q(status=1))
            order_products  = order.orderproduct_set.all()

            results = [
            {
                "product_id"             : order_product.id, 
                "product_option_id"      : order_product.product_option.id,
                "product_name"           : order_product.product_option.product.name,
                "product_color"          : order_product.product_option.color.name,
                "product_size"           : order_product.product_option.size.name,
                "quantity"               : order_product.quantity,
                "product_original_price" : order_product.product_option.product.original_price,
                "product_image"          : order_product.product_option.product.productimage_set.all()[0].image_url,
                "product_price"          : order_product.product_option.product.original_price * (100 - order_product.product_option.product.discount_percentage) / 100,
                "product_company"        : order_product.product_option.product.company.name,
                "product_delivery_type"  : order_product.product_option.product.delivery.method.name,
                "product_delivery_fee"   : order_product.product_option.product.delivery.fee.price,
            } for order_product in order_products]
            
            return JsonResponse({'results':results}, status=200)

        except json.decoder.JSONDecodeError:
            return JsonResponse({'message':'JSON_DECODE_ERROR'}, status=400)
        
        except KeyError:
            return JsonResponse({'message':'KEY_ERROR'}, status=400)
        
        except DataError:
            return JsonResponse({'message':'DATA_ERROR'}, status=400)
        
        except Order.DoesNotExist:
            return JsonResponse({'message':'INVALID_ORDER'}, status=400)
        
        except Order.MultipleObjectsReturned:
            return JsonResponse({'message':'MULTIPLE_ORDER_ERROR'}, status=400)
        
        except OrderProduct.DoesNotExist:
            return JsonResponse({'message':'INVALID_ORDER_PRODUCT'}, status=400)

        except OrderProduct.MultipleObjectsReturned:
            return JsonResponse({'message':'MULTIPLE_ORDER_PRODUCT_ERROR'}, status=400)

    @login_decorator
    def post(self, request):
        """ [Order] 장바구니에서 결제하기
        Args:
            - user: 회원 유효성 검사를 통해 token으로 부터 user 정보를 받는다.
            - id: 구매하고자 하는 상품-옵션 id
            - quantity: 구매하고자 하는 상품-옵션의 수량
        Returns: 
            - posting_list : 조건에 맞는 posting list 반환
        Note:
            - 배송지 입력에 관한 기능 구현안되있음. (장바구니에서 상품 선택 후 구매시 구매완료)
        """
        try:
            user                = request.user
            data                = json.loads(request.body)
            product_option_id   = data['id']
            quantity            = data['quantity']
            total_price         = data['total_price']

            if not product_option_id:
                return JsonResponse({'message' : '구매하실 상품을 선택해 주세요'}, status=400)
            if not Order.objects.filter(Q(user=user)&Q(status=1)).exists():
                return JsonResponse({'message' : '유효하지 않은 접근입니다'}, status=400)

            order_product          = OrderProduct.objects.get(Q(product_option_id=product_option_id)&Q(order__status=1))
            # 장바구니에 담았을때와 비교하여 최종적으로 구매한 수량으로 값 update
            order_product.quantity = quantity
            order_product.save()

            order = Order.objects.get(Q(user=user)&Q(status=1))
            # 최종 주문 후 계산된 가격
            order.total_price = total_price
            order.save()
            order_products = order.orderproduct_set.all()

            # 주문 완료한 상품에 대한 list
            results = [
            {
                "product_id"             : order_product.id, 
                "product_option_id"      : order_product.product_option.id,
                "product_name"           : order_product.product_option.product.name,
                "product_color"          : order_product.product_option.color.name,
                "product_size"           : order_product.product_option.size.name,
                "quantity"               : order_product.quantity,
                "product_original_price" : order_product.product_option.product.original_price,
                "product_image"          : order_product.product_option.product.productimage_set.all()[0].image_url,
                "product_price"          : order_product.product_option.product.original_price * (100 - order_product.product_option.product.discount_percentage) / 100,
                "product_company"        : order_product.product_option.product.company.name,
                "product_delivery_type"  : order_product.product_option.product.delivery.method.name,
                "product_delivery_fee"   : order_product.product_option.product.delivery.fee.price,
            } for order_product in order_products]

            return JsonResponse({'message':results}, status=200)

        except json.decoder.JSONDecodeError:
            return JsonResponse({'message':'JSON_DECODE_ERROR'}, status=400)
        
        except KeyError:
            return JsonResponse({'message':'KEY_ERROR'}, status=400)

        except Order.DoesNotExist:
            return JsonResponse({'message':'INVALID_ORDER'}, status=400)
        
        except Order.MultipleObjectsReturned:
            return JsonResponse({'message':'MULTIPLE_ORDER_ERROR'}, status=400)
        
        except OrderProduct.DoesNotExist:
            return JsonResponse({'message':'INVALID_ORDER_PRODUCT'}, status=400)

        except OrderProduct.MultipleObjectsReturned:
            return JsonResponse({'message':'MULTIPLE_ORDER_PRODUCT_ERROR'}, status=400)