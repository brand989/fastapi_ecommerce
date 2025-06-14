from pydantic import BaseModel


class CreateProduct(BaseModel):
    name: str
    description: str
    price: int
    image_url: str
    stock: int
    category_id: int
    rating: int


class CreateCategory(BaseModel):
    name: str
    parent_id: int | None = None


class CreateUser(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: str
    password: str


class CreateReviews(BaseModel):
    user_id: int
    product_id: int
    comment: str | None = None
    grade: int
