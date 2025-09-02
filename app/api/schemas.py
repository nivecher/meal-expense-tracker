"""API Validation Schemas."""

from marshmallow import Schema, fields


class CategorySchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    description = fields.Str()
    color = fields.Str()
    user_id = fields.Int(dump_only=True)


class RestaurantSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    type = fields.Str()
    description = fields.Str()
    address = fields.Str()
    city = fields.Str()
    state = fields.Str()
    postal_code = fields.Str()
    country = fields.Str()
    phone = fields.Str()
    website = fields.Str()
    email = fields.Email()
    cuisine = fields.Str()
    is_chain = fields.Bool()
    rating = fields.Float()  # User's personal rating (1.0-5.0)
    notes = fields.Str()
    user_id = fields.Int(dump_only=True)
    google_place_id = fields.Str()


class ExpenseSchema(Schema):
    id = fields.Int(dump_only=True)
    amount = fields.Decimal(as_string=True, required=True)
    notes = fields.Str()
    meal_type = fields.Str()
    order_type = fields.Str()
    party_size = fields.Int(allow_none=True, validate=lambda x: x is None or 1 <= x <= 50)
    date = fields.Date(required=True)
    user_id = fields.Int(dump_only=True)
    restaurant_id = fields.Int(required=True)
    category_id = fields.Int(required=True)


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True)
    email = fields.Email(required=True)


class PasswordChangeSchema(Schema):
    old_password = fields.Str(required=True)
    new_password = fields.Str(required=True)
