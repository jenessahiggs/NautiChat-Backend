from fastapi import FastAPI


from src.auth.router import router as auth_router
from src.llm.router import router as llm_router

app = FastAPI()
app.include_router(auth_router, prefix="/auth")
app.include_router(llm_router, prefix="/llm")




# @app.get("/admin/messages")
# def get_all_messages(
#     current_user: Annotated[User, Depends(get_admin_user)],
# ) -> List[Message]:
#     """Get all messages"""
#     return [
#         Message(
#             message_id=1,
#             conversation_id=1,
#             user_id=current_user.user_id,
#             input="Input for message 1",
#             response="Response for message 1",
#         ),
#         Message(
#             message_id=2,
#             conversation_id=2,
#             user_id=current_user.user_id,
#             input="Input for message 2",
#             response="Response for message 2",
#         ),
#     ]
