import json

from django.http            import JsonResponse
from django.views           import View
from django.db.models       import Count

from user.models    import User
from utils     import login_decorator, non_user_accept_decorator
from posting.models import (
        Posting,
        PostingSize,
        PostingHousing,
        PostingStyle,
        PostingSpace,
        PostingLike,
        PostingComment,
        PostingScrap
)

class PostingView(View):
    @non_user_accept_decorator
    def get(self, request):
        """ [Posting] 메인페이지 : 게시글 list
        Args:
            - order_request : query parameter로 들어올 "정렬"조건이 들어있는 dict 형식. 값이 들어오지 않을 경우 기본으로 "최신순"으로 정렬되도록 함.
        User:
            - 비회원일 경우 "request.user"에 None을 담는 decorator 작성 (non_user_accept_decorator)
        Returns: 
            - posting_list : 조건에 맞는 posting list 반환
        """

        user            = request.user
        postings        = Posting.objects.prefetch_related('comment').select_related('user').all()
        order_request   = request.GET.get('order', 'recent')

        # 좋아요, 댓글, 스크랩 순으로 정렬하기 위해 해당 값을 "count"메소드를 사용해 계산하고 query를 annotate 한다.
        postings        = postings.annotate(
                            like_num=Count("postinglike"),
                            comment_num=Count("comment"),
                            scrap_num=Count("postingscrap")
                            )
        # 정렬 조건 고정 : 좋아요 많은 순 / 댓글 많은 순 / 스크랩 많은 순 / 최신순 / 오래된순
        order_prefixes = {
                "best"      : "-like_num",
                "popular"   : "-comment_num",
                "scrap"     : "-scrap_num",
                "recent"    : "-created_at",
                "old"       : "created_at"
                }
        
        # filtering 조건 : 주거형태 / 공간형태 / 평수 / 스타일
        filter_prefixes = {
                'housing'    : 'housing_id__in',
                'space'      : 'space_id__in',
                'size'       : 'size_id__in',
                'style'      : 'style_id__in'
                }

        # request.GET 으로 "filter_prefixes"에 있는 key와 그에 대한 값이 존재할 경우 해당 로직 수행 / id로 받은 값들
        filter_set = {
                filter_prefixes.get(key) : value for (key, value) in dict(request.GET).items() 
                if filter_prefixes.get(key)
                }

        # 결정된 정렬조건과 filtering 조건에 맞게 Posting 객체들을 변수에 담는다.
        postings = postings.filter(**filter_set).order_by(order_prefixes[order_request])
        
        # posting_list 변수에 Posting 객체 각각을 담는다.
        posting_list = [{
                "id"                        : posting.id,
                "card_user_image"           : posting.user.image_url,
                "card_user_name"            : posting.user.name,
                "card_user_introduction"    : posting.user.description,
                "card_image"                : posting.image_url,
                "card_content"              : posting.content,
                "like_status"               : posting.postinglike_set.filter(user=user).exists(),
                "scrap_status"              : posting.postingscrap_set.filter(user=user).exists(),
                "comments" : {
                    "comment_num"               : posting.comment.count(),
                    "comment_user_image"        : posting.comment.first().user.image_url,
                    "comment_user_name"         : posting.comment.first().user.name,
                    "comment_content"           : posting.comment.first().content
                    } if posting.comment.exists() else {
                        "comment_num"               : 0,
                        "comment_user_image"        : None,
                        "comment_user_name"         : None,
                        "comment_content"           : None
                    },
                "like_num"                  : posting.postinglike_set.filter(posting_id=posting.id).count(),
                "scrap_num"                 : posting.postingscrap_set.filter(posting_id=posting.id).count(),
                "created_at"                : posting.created_at
                } for posting in postings
        ]
        return JsonResponse({'message' : posting_list}, status=200)

    @login_decorator
    def post(self, request):
        """ [Posting] 메인페이지 : 게시글 업로드
        Args:
            - size : 평수
            - housing : 주거형태
            - style : 스타일
            - space : 공간형태
            - card_image : 업로드 사진 주소
            - card_content : 게시물 작성 내용
        User:
            - 회원만 허용하도록 한다 (login_decorator)
        Returns: 
            - 200: {'message' : '게시물이 업로드 되었습니다'}
            - 400: 필수 parameter중 하나라도 들어오지 않았을 경우
        """
        try:
            user        = request.user
            data        = json.loads(request.body)
            size_id     = data.get('size', None)
            housing_id  = data.get('housing', None)
            style_id    = data.get('style', None)
            space_id    = data.get('space', None)
            image_url   = data.get('card_image', None)
            content     = data.get('card_content', None)

            # 필수 parameter validation
            if not size_id:
                return JsonResponse({'message' : '평수를 선택해 주세요'}, status=400)
            if not housing_id:
                return JsonResponse({'message' : '주거 형태를 선택해 주세요'}, status=400)
            if not style_id:
                return JsonResponse({'message' : '스타일을 선택해 주세요'}, status=400)
            if not space_id:
                return JsonResponse({'message' : '공간 형태를 선택해 주세요'}, status=400)
            if not image_url:
                return JsonResponse({'message' : '이미지를 업로드 해주세요'}, status=400)
            if not content:
                return JsonResponse({'message' : '게시글 내용을 입력해 주세요'}, status=400)

            Posting.objects.create(
                    user_id     = user.id, 
                    image_url   = image_url, 
                    content     = content, 
                    size_id     = size_id, 
                    housing_id  = housing_id, 
                    style_id    = style_id, 
                    space_id    = space_id
                    )
            return JsonResponse({'message' : '게시물이 업로드 되었습니다'}, status=201)

        except KeyError:
            return JsonResponse({'message' : 'KEY_ERROR'}, status=400)

class CategoryView(View):
    def get(self, request):
        """ [Posting] 메인페이지 : 카테고리, filtering 조건 list
        Returns: 
            - category_condition : 정렬조건과 filtering 조건 목록 반환
        Note:
            - 정렬 조건에 대한 값은 db에 저장된 형태가 없어 코드상에서 제작함
            - filtering조건들이 각각 정규화 되어 있기 때문에 코드상에서 직접 id를 지정해줌
        """
        # 정렬 조건에 대한 값
        sortings    = [
                {"id" : 1, "name" : "역대인기순", "Ename" : "best"},
                {"id" : 2, "name" : "댓글많은순", "Ename" : "popular"},
                {"id" : 3, "name" : "스크랩많은순", "Ename" : "scrap"},
                {"id" : 4, "name" : "최신순", "Ename" : "recent"},
                {"id" : 5, "name" : "오래된순", "Ename" : "old"}
        ]
        
        # 정렬조건과 filtering 조건을 하나의 table에 작성된 값 처럼 id를 지정해줌.
        category_condition = {
                "categories" : [
                    {
                        "id" : 1,
                        "categoryName"  : "정렬",
                        "categoryEName" : "order",
                        "category"      : [name for name in list(sortings)]
                        },
                    {
                        "id" : 2,
                        "categoryName"  : "주거형태",
                        "categoryEName" : "housing",
                        "category"      : [name for name in list(PostingHousing.objects.values().order_by('id'))]
                    },
                    {
                        "id" : 3,
                        "categoryName"  : "공간",
                        "categoryEName" : "space",
                        "category"      : [name for name in list(PostingSpace.objects.values().order_by('id'))]
                    },
                    {
                        "id" : 4,
                        "categoryName"  : "평수",
                        "categoryEName" : "size",
                        "category"      : [name for name in list(PostingSize.objects.values().order_by('id'))]
                    },
                    {
                        "id" : 5,
                        "categoryName"  : "스타일",
                        "categoryEName" : "style",
                        "category"      : [name for name in list(PostingStyle.objects.values().order_by('id'))]
                    }]
                }
        return JsonResponse({'categories' : category_condition}, status=200)

class PostingLikeView(View):
    @login_decorator
    def post(self, request):
        """ [Posting] 메인페이지 : 게시글 좋아요 기능
        Args:
            - user : header에 담긴 user의 토큰으로부터 user 정보 판단 (login_decorator)
            - posting_id : body에 담겨져서 들어온 posting의 id
        Returns: 
            - 201: 기존에 user가 해당 게시물을 "좋아요" 하지 않은 상태일 경우 유저와 게시글 간의 "좋아요" 관계 생성
            - 204: 기존에 user가 해당 게시물을 이미 "좋아요" 한 상태일 경우 기존의 "좋아요"상태를 삭제 (hard_delete)
            - 400: body에 담겨온 id값을 지닌 posting이 없을 경우 에러 반환
        """
        user        = request.user
        data        = json.loads(request.body)
        print("data???????????", data)
        posting_id  = data['posting_id']
        if not Posting.objects.get(id=posting_id):
            return JsonResponse({'message' : '존재하지 않는 posting 입니다'}, status=400)
        
        if PostingLike.objects.filter(user_id=user.id, posting_id=posting_id):
            PostingLike.objects.filter(user_id=user.id, posting_id=posting_id).delete()
            return JsonResponse({'message' : '게시물 좋아요 취소'}, status=204)
        
        PostingLike.objects.create(user_id=user.id, posting_id=posting_id)
        return JsonResponse({'message' : '게시물 좋아요 완료'}, status=201)

class PostingScrapView(View):
    @login_decorator
    def post(self, request):
        """ [Posting] 메인페이지 : 게시글 스크랩 기능
        Args:
            - user : header에 담긴 user의 토큰으로부터 user 정보 판단 (login_decorator)
            - posting_id : body에 담겨져서 들어온 posting의 id
        Returns: 
            - 201: 기존에 user가 해당 게시물을 "스크랩" 하지 않은 상태일 경우 유저와 게시글 간의 "스크랩" 관계 생성
            - 204: 기존에 user가 해당 게시물을 이미 "스크랩" 한 상태일 경우 기존의 "스크랩"상태를 삭제 (hard_delete)
            - 400: body에 담겨온 id값을 지닌 posting이 없을 경우 에러 반환
        """
        data       = json.loads(request.body)
        user       = request.user
        posting_id = data['posting_id']

        if not PostingScrap.objects.get(posting_id=posting_id):
            return JsonResponse({'message' : '존재하지 않는 posting 입니다'}, status=400)

        if PostingScrap.objects.filter(user_id=user.id, posting_id=posting_id):
            PostingScrap.objects.filter(user_id=user.id, posting_id=posting_id).delete()
            return JsonResponse({'message' : '게시물 스크랩 취소'}, status=204)

        PostingScrap.objects.create(user_id=user.id, posting_id=posting_id)
        return JsonResponse({'message' : '게시물 스크랩 완료'}, status=201)