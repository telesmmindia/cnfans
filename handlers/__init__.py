from aiogram import Router

def get_handlers_router() -> Router:
    from . import  account, order, start
    router = Router()
    router.include_router(account.router)
    #router.include_router(acnt.router)
    router.include_router(order.router)
    router.include_router(start.router)

    return router