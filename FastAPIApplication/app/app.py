from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from app.schemas import PostCreate, PostResponse, UserCreate, UserRead, UserUpdate
from app.db import Post, create_db_and_tables, get_async_session, User
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select
from app.images import imagekit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
import shutil
import os
import uuid
import tempfile

from app.users import auth_backend, current_active_user, fastapi_users

@asynccontextmanager
async def lifespan(app:FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(fastapi_users.get_auth_router(auth_backend), prefix='/auth/jwt', tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix='/auth', tags=["auth"])
app.include_router(fastapi_users.get_reset_password_router(), prefix='/auth', tags=["auth"])
app.include_router(fastapi_users.get_verify_router(UserRead), prefix='/auth', tags=["auth"])
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix='/users', tags=["users"])

@app.post("/upload")
async def upload_file(
        file: UploadFile = File(...),
        caption: str = Form(""),
        user: User = Depends(current_active_user),
        session: AsyncSession = Depends(get_async_session)
):
    temp_file_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        print(f"Filename : {file.filename}")
        upload_result = imagekit.upload_file(
            file=open(temp_file_path, "rb"),
            file_name = file.filename,
            options=UploadFileRequestOptions(
                use_unique_file_name=True,
                tags=["backend-upload"]
            )
        )

        print(f"upload_result.file_name : {upload_result.name}")
        print(f"Return : {upload_result.response_metadata.http_status_code}")
        if upload_result.response_metadata.http_status_code == 200:
            try:
                post = Post(
                    user_id=user.id,
                    caption=caption,
                    url=upload_result.url,
                    file_type="video" if file.content_type.startswith("video/") else "photo",
                    file_name=upload_result.name
                )
                print(f"Post created successfully: {post}")
                session.add(post)
                await session.commit()
                await session.refresh(post)
                print(f"Post created successfully: {post}")
            except Exception as e:
                print(f"Exception adding post in session: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
            return post
        else:
            raise HTTPException(status_code=upload_result.response_metadata.http_status_code,
                                detail=upload_result.response_metadata.error)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        file.file.close()


    return post
@app.get("/feed")
async def get_feed(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_active_user),
):
    result = await session.execute(select(Post).order_by(Post.created_at.desc()))
    posts = [row[0] for row in result.all()]

    result  = await session.execute(select(User))
    users = [row[0] for row in result.all()]
    user_dict = {u.id : u.email for u in users}

    posts_data = []
    for post in posts:
        posts_data.append(
            {
                "id": str(post.id),
                "user_id": str(post.user_id),
                "caption": post.caption,
                "url": post.url,
                "file_type": post.file_type,
                "file_name": post.file_name,
                "created_at": post.created_at.isoformat(),
                "is_owner": post.user_id == user.id,
                "email": user_dict.get(post.user_id, "Unknown User"),
            }
        )
    return {"posts": posts_data}


@app.delete("/posts/{post_id}")
async def delete_post(post_id: str, session: AsyncSession = Depends(get_async_session),
                      user: User = Depends(current_active_user)):
    try:
        post_uuid = uuid.UUID(post_id)

        result = await session.execute(select(Post).where(Post.id == post_uuid))
        post = result.scalars().first()

        if not post:
            raise HTTPException(status_code=404, details="Post not found")

        if post.user_id != user.id:
            raise HTTPException(status_code=403, details="You are not authorized to delete this post")

        await session.delete(post)
        await session.commit()

        return {"success": True, "message": "Post deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
"""
################# Basic Understanding #################
# 
# # # Basic Test Endpoint
# # @app.get("/hello-world")
# # def hello_world():
# #     return {"message": "Hello World"} # JSON : Javascript Object Notation
# 
# text_posts = {1: {"title": "First Post", "content": "This is the content of the first post"},
#               2: {"title": "Second Post", "content": "This is the content of the second post"},
#               3: {"title": "Third Post", "content": "This is the content of the third post"},
#               4: {"title": "Fourth Post", "content": "This is the content of the fourth post"},
#               5: {"title": "Fifth Post", "content": "This is the content of the fifth post"},
#               6: {"title": "Sixth Post", "content": "This is the content of the sixth post"},
#               7: {"title": "Seventh Post", "content": "This is the content of the seventh post"},
#               8: {"title": "Eighth Post", "content": "This is the content of the eighth post"},
#               9: {"title": "Ninth Post", "content": "This is the content of the ninth post"},
#               10: {"title": "Tenth Post", "content": "This is the content of the tenth post"},
#               }
# 
# @app.get("/posts")
# def get_all_posts(limit: int = None)->dict[int, PostCreate]:
#     if limit:
#         return {k: v for k, v in text_posts.items() if k <= limit}
#         
#     return text_posts
# 
# 
# @app.get("/posts/{post_id}")
# def get_post(post_id: int) -> PostCreate:
# 
#     if post_id not in text_posts:
#         raise HTTPException(status_code=404, detail="Post not found")
#     
#     return text_posts[post_id]
# 
# @app.post("/posts")
# def create_post(post: PostCreate) -> PostCreate:
#     post_id = max(text_posts.keys()) + 1
#     text_posts[post_id] = {"title": post.title, "content": post.content}
#     return text_posts[post_id]
# 
# @app.delete("/posts/{post_id}")
# def delete_post(post_id: int) -> dict[str, str]:
#     if post_id not in text_posts:
#         raise HTTPException(status_code=404, detail="Post not found")
#     del text_posts[post_id]
#     return {"message": "Post deleted successfully"}
"""