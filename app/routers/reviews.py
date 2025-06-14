from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from sqlalchemy import insert, select, func, update

from app.backend.db_depends import get_db

from app.schemas import CreateReviews
from app.models.products import Product
from app.models.reviews import Review

from app.routers.auth import get_current_user

router = APIRouter(prefix='/reviews', tags=['reviews'])


async def recalc_product_rating(db: AsyncSession, product_id: int) -> float:

    avg_stmt = select(func.coalesce(func.avg(Review.grade), 0.0)).where(
        Review.is_active == True,
        Review.product_id == product_id
    ).scalar_subquery()

    await db.execute(update(Product).where(Product.id == product_id).values(rating=avg_stmt))

    await db.commit()

    new_rating = await db.scalar(
        select(func.coalesce(func.avg(Review.grade), 0.0))
        .where(Review.is_active == True, Review.product_id == product_id)
    )

    return float(new_rating or 0.0)


@router.get('/')
async def all_reviews(db: Annotated[AsyncSession, Depends(get_db)]):
    reviews = await db.scalars(
        select(Review).join(Product).where(Product.is_active == True,
                                           Review.is_active == True, Product.stock > 0))

    all_reviews = reviews.all()

    if not all_reviews:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There are no product'
        )
    return all_reviews


@router.get('/{product_slug}')
async def products_reviews(db: Annotated[AsyncSession, Depends(get_db)], product_slug: str):
    reviews = await db.scalars(
        select(Review).join(Product).where(Product.is_active == True,
                                           Review.is_active == True, Product.stock > 0, Product.slug == product_slug))

    all_reviews = reviews.all()

    if not all_reviews:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There are no product'
        )
    return all_reviews


@router.post('/', status_code=status.HTTP_201_CREATED)
async def add_review(db: Annotated[AsyncSession, Depends(get_db)],
                     create_review: CreateReviews,
                     get_user: Annotated[dict, Depends(get_current_user)]):
    if get_user.get('is_customer'):
        product = await db.scalar(select(Product).where(Product.id == create_review.product_id))

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='There is no category found'
            )

        await db.execute(insert(Review).values(user_id=get_user.get('id'),
                                               product_id=create_review.product_id,
                                               comment=create_review.comment,
                                               grade=create_review.grade))

        rating_message = await recalc_product_rating(db, create_review.product_id)

        await db.commit()

        return {
            'status_code': status.HTTP_201_CREATED,
            'transaction': 'Successful',
            'rating_message': rating_message
        }

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You are not authorized to use this method'
        )


@router.delete('/{review_id}')
async def delete_review(review_id: int,
                        db: Annotated[AsyncSession, Depends(get_db)],
                        get_user: Annotated[dict, Depends(get_current_user)]):
    if get_user.get('is_admin'):
        review = await db.scalar(select(Review).where(Review.id == review_id))
        if review is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='There is no category found'
            )
        review.is_active = False

        await db.commit()

        rating_message = await recalc_product_rating(db, review.product_id)

        return {
            'status_code': status.HTTP_200_OK,
            'transaction': 'Category delete is successful',
            'rating_message': rating_message
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You must be admin user for this'
        )
