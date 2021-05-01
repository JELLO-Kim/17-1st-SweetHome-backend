import json

from django.http      import JsonResponse
from django.views     import View
from django.db.models import Avg, Count, Q

from user.models    import User
from product.models import (
  Product, 
  ProductReview, 
  ReviewLike,
  ProductOption,
  ProductColor,
  ProductSize,
  Category
)
from order.models   import OrderProduct, Order, OrderStatus
from utils     import login_decorator

DISCOUNT_PROUDCTS_COUNT = 5

class CategoryView(View):
    def get(self, request):
        """ [Product] 상품의 category list 반환
        Returns: 
            - category_list: 카테고리 목록
        Note:
            - 출력 예시: 메인 category (가구) > 서브 카테고리 (소파/거실가구) > 상세 카테고리 (리클라이너 소파)
            - 서브 카테고리에 따라 상세 카테고리 항목이 없을 수 있다.
        """
        category_list = [{
            'id': category.id,
            'name': category.name,
            'sub_category': [{
                'id': sub_category.id,
                'name': sub_category.name,
                'detail_category' : [{
                    'id': detail_category.id,
                    'name': detail_category.name
                } for detail_category in sub_category.detailcategory_set.all()]
            } for sub_category in category.subcategory_set.all()]
        } for category in Category.objects.all().order_by('id')]
        return JsonResponse({'categories': category_list}, status=200)

class ProductView(View):
    def get(self, request):
        """ [Product] 상품 list
        Args:
            - order_condition: 'order'라는 키값에 담길 정렬 조건. 값이 들어오지 않을 경우 None 처리한다.
            - top_list_condition: 상품 메인페이지에서 상단에 보여질 할인상품 목록에 대한 조건. 값이 들어오지 않을 경우 None 처리한다.
        Returns: 
            - products_list: 상품 목록
            - count: 상품의 총 갯수
        Note:
            - 출력 예시: 메인 category (가구) > 서브 카테고리 (소파/거실가구) > 상세 카테고리 (리클라이너 소파)
            - 서브 카테고리에 따라 상세 카테고리 항목이 없을 수 있다.
        """
        # 상품의 정렬 조건
        order_condition    = request.GET.get('order', None)
        # 상품 메인페이지의 할인상품 조건
        top_list_condition = request.GET.get('top', None)

        # query parameter로 들어올 filtering 조건 기본 값 dictionary
        filter_prefixes = {
            'category'       : 'detail_category__sub_category__category__in',
            'subcategory'    : 'detail_category__sub_category__in',
            'detailcategory' : 'detail_category__in',
            'color'          : 'productoption__color__in',
            'size'           : 'productoption__size__in'
        }

        # id로 들어온 filtering 조건에 맞춰 filter_set 이라는 변수에 조건을 담는다
        filter_set = {
            filter_prefixes.get(key) : value for (key, value) in dict(request.GET).items() if filter_prefixes.get(key)
        }

        # filtering 조건에 맞춰 Product 객체 불러오기
        '''
        - DB hit을 고려하여 select_related와 prefetch_related 사용
        - 설정된 filtering 조건 적용 (**filter_set)
        - annotate사용: 상품 리뷰의 별점(rate)값의 평균을 계산해서 하나의 값으로 데이터 반환
        '''
        products = Product.objects.select_related('company', 'delivery__fee')\
            .filter(**filter_set)\
            .prefetch_related('productimage_set', 'productreview_set')\
            .annotate(rate_average=Avg('productreview__rate')).distinct()
        
        # 시간에 따른 정렬조건: 최신순 / 오래된 순
        order_by_time  = {'recent' : 'created_at', 'old' : '-created_at'}
        # 가격에 따른정렬조건: 저가순 / 고가순
        order_by_price = {'min_price' : 'discount_price', 'max_price' : '-discount_price'}

        # 정렬 조건이 시간에 따랐을 경우
        if order_condition in order_by_time:
            products = products.order_by(order_by_time[order_condition])

        # 정렬 조건이 가격에 따랐을 경우
        if order_condition in order_by_price:
            # extra(): 메인 query에 sql문을 추가하여 반영할 수 있는 메소드 / 정가에서 할인률을 계산한 값을 가져오기 위해 사용
            products = products.extra(
                    select={'discount_price' : 'original_price * (100 - discount_percentage) / 100'}).order_by(
                    order_by_price[order_condition])
        # 정렬 조건이 리뷰순일 경우 (리뷰 많은 순)
        if order_condition == 'review':
            products = products.annotate(review_count=Count('productreview')).order_by('-review_count')
        # 상품 메인페이지의 할인중인 상품 조건이 필요할 경우 (해당 목록은 5개의 상품만 반환한다) / 5개의 상품목록에 대해 위와 같은 조건의 정보를 담는다   
        if top_list_condition == 'discount': 
            products = Product.objects.select_related('company', 'delivery__fee')\
                .prefetch_related('productimage_set', 'productreview_set')\
                .annotate(rate_average=Avg('productreview__rate'))\
                .order_by('-discount_percentage')[:DISCOUNT_PROUDCTS_COUNT]

        # products_list : 불러온 Product 객체들을 반복문을 통해 각각의 정보를 가공한다.
        products_list = [{
            'id'                  : product.id,
            'name'                : product.name,
            'discount_percentage' : int(product.discount_percentage),
            'discount_price'      : int(product.original_price) * (100 - int(product.discount_percentage)) // 100,
            'company'             : product.company.name,
            'image'               : product.productimage_set.all()[0].image_url,
            'rate_average'        : round(product.rate_average, 1) if product.rate_average else 0,
            'review_count'        : product.productreview_set.count(),
            'is_free_delivery'    : product.delivery.fee.price == 0,
            'is_on_sale'          : not (int(product.discount_percentage) == 0),
            } for product in products
        ]
        # 불러온 product 객체들의 총 갯수 반환
        products_count = products.count()

        return JsonResponse({'products' : products_list, 'count' : products_count}, status=200)

class ProductDetailView(View):
    def get(self, request, product_id):
        """ [Product] 상품 상세 페이지
        Args:
            - product_id: path paramter로 들어오는 선택한 상품 id
        Returns: 
            - 200: {'product': 상품의 상세 정보}
            - 404: 유효하지 않은 상품 id로 접근했을 경우
        """
        if not Product.objects.filter(id=product_id).exists():
            return JsonResponse({'message':'존재하지 않는 상품입니다'}, status=404)

        product = Product.objects.get(id=product_id)

        product_detail = {
            'id'                  : product.id,
            'name'                : product.name,
            'original_price'      : int(product.original_price),
            'discount_percentage' : int(product.discount_percentage),
            'discount_price'      : int(product.original_price) * (100 - int(product.discount_percentage)) // 100,
            'company'             : product.company.name,
            'image'               : [i.image_url for i in product.productimage_set.all()],
            'rate_average'        : round(product.productreview_set.aggregate(Avg('rate'))['rate__avg'], 1)\
                if product.productreview_set.aggregate(Avg('rate'))['rate__avg'] else 0,
            'review_count'        : product.productreview_set.count(),
            'delivery_type'       : product.delivery.method.name,
            'delivery_period'     : product.delivery.period.day,
            'delivery_fee'        : product.delivery.fee.price,
            'is_free_delivery'    : product.delivery.fee.price == 0,
            'is_on_sale'          : not (int(product.discount_percentage) == 0),
            'size'                : list(set([i.size.name for i in product.productoption_set.all()])),
            'color'               : list(set([i.color.name for i in product.productoption_set.all()])),
        }
        return JsonResponse({'product': product_detail}, status=200)

class ProductReviewView(View):
    def get(self, request, product_id):
        """ [Product] 단일 상품(in 상품 상세 페이지)의 리뷰 목록
        Args:
            - product_id: path paramter로 들어오는 선택한 상품 id
            - rate: filtering 조건에 필요한 별점 조건
            - order: 정렬조건에 필요한 dict값. 지정된 값이 없을 경우 기본적으로 "최신순"으로 정렬된다.
            - like: 
        Returns: 
            - 200: {'result': 상품의 리뷰정보}
            - 200 (리뷰가 없는 상품일 경우): {'results' : '리뷰가 존재하지 않는 상품입니다'}
            - 404: 유효하지 않은 상품 id로 접근했을 경우
        Note:
            - Q(): 리뷰를 별점별로 확인할때 여러 조건 선택 가능 / Q()를 사용해 or 조건으로 SQL문의 WHERE 구문 지정 + product_id도 Q()로 함께 처리해주었다.
        """
        if not Product.objects.get(id=product_id):
            return JsonResponse({'message':'존재하지 않는 상품입니다'}, status=404)

        product   = Product.objects.get(id=product_id)
        if not product.productreview_set.all():
            return JsonResponse({'results' : '리뷰가 존재하지 않는 상품입니다'}, status=200)
        order     = request.GET.get('order', 'recent')
        rate_list = request.GET.getlist('rate', None)

        # Q()를 활용한 filtering 구현
        '''
        if => 지정된 filtering조건(OR 조건) + (AND 조건)path parameter로 들어온 product의 id
        else (별점에 따른 filtering 조건이 없을 때) => path parameter로 들어온 product의 id
        '''
        if rate_list:
            q = Q()
            for rate in rate_list:
                q.add(Q(rate=rate), q.OR)
            q.add(Q(product=product), q.AND)
        else:
            q = Q(product=product)

        # 정렬 조건: 최신순 / 오래된순 / 리뷰 많은 순
        order_dict = {
            'recent':'-created_at',
            'old'   : 'created_at',
            'like'  :'-review_like'
        }

        # filtering 조건과 정렬 조건에 따라 ProductReview 객체 불러오기
        product_reviews = ProductReview.objects.filter(q)\
            .annotate(review_like=Count('reviewlike')).order_by(order_dict[order])
        
        review_list = [{
                    "review_id"        : product_review.id,
                    "review_content"   : product_review.content,
                    "review_image"     : product_review.image_url,
                    "review_rate"      : product_review.rate,
                    "product_name"     : product.name,
                    "day"              : str(product_review.created_at).split(" ")[0],
                    "review_user_name" : product_review.user.name,
                    "review_like"      : product_review.review_like,
                } for product_review in product_reviews]

        return JsonResponse({'results':review_list}, status=200)

class ReviewLikeView(View):
    @login_decorator
    def post(self, request, product_id):
        """ [Product] 단일 상품(in 상품 상세 페이지)의 리뷰에 "좋아요" 달기
        Args:
            - product_id: path paramter로 들어오는 선택한 상품 id
            - review_id: request body로 들어오는 선택된 review의 id
        Returns: 
            - 201: {'message': '리뷰 좋아요 완료'}
            - 204: {'message': '리뷰 좋아요 취소'}
            - 404: 유효하지 않은 상품 id로 접근했을 경우
            - 400: 리뷰가 선택되지 않았을 경우
        """
        try:
            user      = request.user
            data      = json.loads(request.body)
            review_id = data['review_id']

            if not ProductReview.objects.get(id=review_id):
                return JsonResponse({'message':'존재하지 않는 리뷰입니다'}, status=404)
            product_review = ProductReview.objects.get(id=review_id)
            if user.productreview_set.filter(id=review_id).exists():
                return JsonResponse({'message':'회원님이 직접 작성한 리뷰입니다'}, status=400)
            # get_or_create 활용
            '''
            get 조건: 이미 유저가 해당 리뷰를 "좋아요" 했을 경우 해당되는 row 를 가져온다 => review_like 라는 변수에 해당 데이터 담음
            create 조건: "좋아요" 관계 기록이 없어 이에 대한 새로운 row가 생성된다. => create 라는 변수에 생성된 row 담음
            '''
            review_like, created = ReviewLike.objects.get_or_create(review=product_review, user=user)
            # get이었을 경우 두번째의 기능은 "삭제" 처리이다.
            if not created:
                review_like.delete()
                return JsonResponse({'message' : "리뷰 좋아요 취소"}, status=204)

            return JsonResponse({'message':'리뷰 좋아요 완료'}, status=201)

        except KeyError:
            return JsonResponse({'message' : '리뷰가 선택되지 않았습니다'}, status=400)
        except json.decoder.JSONDecodeError:
            return JsonResponse({'message':'JSON_DECODE_ERROR'}, status=400)

class ProductCartView(View):
    @login_decorator
    def post(self, request):
        """ [Product] 장바구니에 상품 담기 구현
        Args:
            - color: 상품의 색상 옵션(id가 아닌 name값으로 받는다)
            - size: 상품의 크기 옵션(id가 아닌 name값으로 받는다)
            - id: 선택된 상품의 id값
            - quantity: 선택된 상품-옵션 의 수량
        Returns: 
            - 201 (신규 내역 추가): {'message': '장바구니에 새로 추가되었습니다'}
            - 201 (기존 내역에서 갯수 추가): {'message':'기존 장바구니 내역에서 갯수가 추가되었습니다'}
            - 400: validation 부적합 (상품, 색상, 사이즈, 상품-옵션 조합, 수량)
        Note:
            - update_or_create: 이미 존재하는 장바구니 옵션이라면 수량만 update, 그게 아니라면 새로 생성한다
        """
        try:
            user       = request.user
            data       = json.loads(request.body)
            product_id = data['id']

            # 상품 validation            
            if not Product.objects.filter(id=product_id).exists():
                return JsonResponse({'message':'존재하지 않는 상품입니다'}, status=404)
            # 상품 옵션 validation
            if 'color' not in data:
                return JsonResponse({'message' : '색상을 선택해 주세요'}, status=400)
            if 'size' not in data:
                return JsonResponse({'message' : '사이즈를 선택해 주세요'}, status=400)
            # 색상 옵션과 사이즈 옵션 key validation 통과 후
            color = ProductColor.objects.get(name=data['color'])
            size  = ProductSize.objects.get(name=data['size'])
            # 상품-옵션 조합 validation
            if not ProductOption.objects.filter(
                product_id=product_id,color=color, size=size
            ).exists():
                return JsonResponse({'message':'유효하지 않는 상품 옵션입니다'}, status=404)
            # 상품-옵션 수량 validation
            if 'quantity' not in data:
                return JsonResponse({'message' : '수량을 선택해주세요'}, status=400)

            quantity = int(data['quantity'])
            product_option = ProductOption.objects.get(
                product_id=product_id,color=color, size=size
            )
            order = Order.objects.update_or_create(user=user, status_id=1)[0]
            # 장바구니에 넣은 상태(order__status=1)일 경우 기존 값을 수정한다 
            if OrderProduct.objects.filter(order=order, product_option=product_option, order__status=1).exists(): 
                order_product = OrderProduct.objects.get(order=order, product_option=product_option)
                # 기존에 있는 상품-옵션 항목에 수량이 추가된 경우라면 수량만 추가해서 저장한다
                order_product.quantity+=quantity
                order_product.save()
                return JsonResponse({'message':'기존 장바구니 내역에서 갯수가 추가되었습니다'}, status=201)
            # 새로 생성되는 장바구니 목록일 경우 create
            else:
                OrderProduct.objects.create(
                    order=order, product_option=product_option, quantity=quantity
                )
            
            return JsonResponse({'message':'장바구니에 새로 추가되었습니다'}, status=201)

        except json.decoder.JSONDecodeError:
            return JsonResponse({'message':'JSON_DECODE_ERROR'}, status=400)
