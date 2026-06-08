from django.urls import path
from users.views.user_login_view import LoginUserAPIView
from users.views.user_profile_view import UserProfileAPIView
from users.views.user_register_view import RegisterUserAPIView
from users.views.follow_view import FollowUserAPIView
from users.views.senescyt_view import VerifySenescytAPIView
from users.views.user_search_view import UserSearchView
from users.views.email_verification_view import VerifyEmailAPIView, ResendVerificationEmailAPIView
from users.views.social_auth_view import SocialAuthAPIView

urlpatterns = [
    path('users/register/', RegisterUserAPIView.as_view(), name='register_user'),
    path('users/login/', LoginUserAPIView.as_view(), name='login_user'),
    path('users/social-auth/', SocialAuthAPIView.as_view(), name='social_auth'),
    path('users/search/', UserSearchView.as_view(), name='user_search'),
    path('users/<int:userid>/', UserProfileAPIView.as_view(), name='user_profile'),
    path('users/<int:userid>/follow/', FollowUserAPIView.as_view(), name='follow_user'),
    path('users/<int:userid>/verify-senescyt/', VerifySenescytAPIView.as_view(), name='verify_senescyt'),
    path('users/verify-email/<uuid:token>/', VerifyEmailAPIView.as_view(), name='verify_email'),
    path('users/resend-verification/', ResendVerificationEmailAPIView.as_view(), name='resend_verification'),
]
