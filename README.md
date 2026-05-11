# QueVesVe!& Backend

## Description

Backend del aplicativo **QueVesVe!&**, una plataforma de videos cortos. Contiene el código del servidor y los endpoints de la API REST.

## Features

### 1) Users (90%):
- **User Registration**: Allows new users to create an account. `POST /users/register`
- **User Login**: Authentication for user access. `POST /users/login`
- **Get User Profile**: View specific user profile information. `GET /users/{userid}`
- **Update User Profile**: Allows users to modify their profile. `PUT /users/{userid}`
- **Delete User**: Remove a user from the system. `DELETE /users/{userid}`

### 2) Videos (TO DO 🚧):
- **Upload Video**: Users can upload videos. `POST /videos`
- **Get Video Details**: View specific details of a video. `GET /videos/{videoid}`
- **List Videos**: Get a list of all available videos. `GET /videos`
- **Delete Video**: Allows users to delete their videos. `DELETE /videos/{videoid}`

### 3) Interactions and Social Network (TO DO 🚧):
- **Like a Video**: Users can 'like' videos. `POST /videos/{videoid}/like`
- **Unlike a Video**: Remove 'like' from a video. `DELETE /videos/{videoid}/like`
- **Comment on a Video**: Post comments on videos. `POST /videos/{videoid}/comment`
- **Delete Comment**: Delete own comments from a video. `DELETE /videos/{videoid}/comment/{commentid}`
- **Follow a User**: Follow other users. `POST /users/{userid}/follow`
- **Unfollow a User**: Unfollow other users. `DELETE /users/{userid}/follow`

### 4) Feed and Discoveries (TO DO 🚧):
- **Get Video Feed**: View a personalized feed of videos. `GET /feed`
- **Search Videos/Users**: Search functionality in the platform. `GET /search`


## Technologies Used

- Python
- Django
- Django Rest Framework
- Django Rest Framework-simplejwt
- PostgreSQL
- pylint (for linting)
- JWT (JSON Web Tokens) for authentication

## Getting Started

1. Clone the repository
2. Install the dependencies: `pipenv install Pipfile`
3. Set up the environment variables (database connection, Postgres credentials)
4. Start the server: `python manage.py runserver`

## Contributing

Contributions are welcome! PRs must have a minimum of 80% test coverage to be accepted.

## License

This project is licensed under the [BSD 3-Clause](LICENSE).
