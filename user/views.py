import json
import bcrypt
import jwt

from django.views import View
from django.http  import JsonResponse

from my_settings  import SECRET_KEY, ALGORITHM
from utils       import login_decorator
from .models      import User

MINIMUM_PASSWORD_LENGTH = 8
MINIMUM_NAME_LENGTH = 2
MAXIMUN_NAME_LENGTH = 15

class SignupView(View):
    def post(self, request):
        """ [User] 회원가입
        Args:
            - email: 유저의 email
            - password: 유저의 password
            - name: 유저의 닉네임
        Returns: 
            - 400 (비밀번호가 너무 짧습니다): 비밀번호가 8자 미만일 경우
            - 400 (이메일을 입력해주세요): 이메일을 입력하지 않았을 경우
            - 400 (비밀번호를 입력해주세요): 비밀번호를 입력하지 않았을 경우
            - 400 (닉네임을 입력해주세요): 닉네임을 입력하지 않았을 경우
            - 400 (닉네임 길이를 맞춰주세요): 닉네임 길이가 유효하지 않을 경우 (2자 이상 15자 이하)
            - 400 (이미 존재하는 닉네임입니다): 닉네임 중복 유효성에 위배될 경우
        Note:
            - 유효한 비밀번호는 bcrypt로 암호화 되어 db에 저장
        """
        try:
            data     = json.loads(request.body)
            email    = data['email']
            password = data['password']                                
            name     = data['name']

            if len(password) < MINIMUM_PASSWORD_LENGTH:
                return JsonResponse({'message' : '비밀번호가 너무 짧습니다'}, status = 400)
            if email not in data:
                return JsonResponse({'message' : '이메일을 입력해주세요'}, status = 400)
            if password not in data:
                return JsonResponse({'message' : '비밀번호를 입력해주세요'}, status = 400)
            if name not in data:
                return JsonRespone({'message' : '닉네임을 입력해주세요'}, status = 400)
            if len(name) < MINIMUM_NAME_LENGTH and len(name) > MAXIMUN_NAME_LENGTH:
                return JsonResponse({'message' : '닉네임 길이를 맞춰주세요'}, status = 400)
            if User.objects.filter(name = name).exists():
                return JsonResponse({'message' : '이미 존재하는 닉네임입니다'}, status = 400)

            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            User.objects.create(
                email    = email,
                password = hashed_password,
                name     = name,
            )
            return JsonResponse({'message' : '회원가입이 완료되었습니다'}, status = 201)
                
        except KeyError:
            return JsonResponse({'message' : 'KEY_ERROR'}, status = 400)


class SigninView(View):
    def post(self, request):
        """ [User] 회원가입
        Args:
            - email: 유저의 email
            - password: 유저의 password
            - name: 유저의 닉네임
        Returns: 
            - 200: {'message' : '로그인 성공', 'access_token' : 유효한 토큰 정보 반환}
            - 401 (존재하지 않는 이메일 입니다): 회원가입된 정보와 일치하는 이메일이 없을 경우
            - 401 (비밀번호를 확인해주세요): 입력한 이메일 정보는 있지만 비밀번호가 동일하지 않을 경우
        Note:
            - 로그인 성공 후 access_token 반환 (body)
        """
        try: 
            data     = json.loads(request.body)
            email    = data['email']
            password = data['password']

            if not User.objects.filter(email = email).exists():
                return JsonResponse({'mesage' : '존재하지 않는 이메일 입니다.'}, status = 401)
            user = User.objects.get(email=email)
            
            if bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
                token = jwt.encode({'user_id': user.id}, SECRET_KEY, ALGORITHM)
                return JsonResponse({'message': '로그인 성공', 'access_token': token}, status=200)
            return JsonResponse({'message': '비밀번호를 확인해주세요'}, status=401)

        except KeyError:
            return JsonResponse({'message': 'KEY_ERROR'}, status=400)


