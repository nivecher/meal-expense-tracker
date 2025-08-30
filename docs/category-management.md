# Category Management Guide

This guide explains how to manage expense categories in the Meal Expense Tracker application.

## 📍 **How Categories Work**

- **User-Specific**: Each user gets their own set of categories
- **Auto-Created**: Default categories are created when a user adds their first expense
- **Customizable**: Users can add, edit, and delete their own categories
- **Centralized Definition**: All default categories are defined in one place

## 🎯 **Current Default Categories**

When a new user adds their first expense, these categories are automatically created:

| Category         | Description                        | Color  | Icon          |
| ---------------- | ---------------------------------- | ------ | ------------- |
| Restaurants      | Restaurant meals and takeout       | Orange | utensils      |
| Groceries        | Grocery shopping and food supplies | Green  | shopping-cart |
| Drinks           | Beverages, coffee, and drinks      | Cyan   | coffee        |
| Fast Food        | Quick service and fast food        | Red    | hamburger     |
| Entertainment    | Movies, events, and entertainment  | Purple | theater-masks |
| Snacks & Vending | Snacks and vending machines        | Blue   | car           |
| Other            | Miscellaneous expenses             | Gray   | question      |

## 🔧 **How to Modify Default Categories**

### **Option 1: Edit the Constants File (Affects New Users Only)**

To change what categories new users get, edit `app/constants/categories.py`:

```python
DEFAULT_CATEGORIES: List[CategoryData] = [
    {
        "name": "Your Category Name",
        "description": "Description of the category",
        "color": "#fd7e14",  # Hex color code
        "icon": "icon-name"   # Font Awesome icon name
    },
    # Add more categories here...
]
```

**Note**: This only affects NEW users. Existing users keep their current categories.

### **Option 2: Update Existing Users' Categories**

To add new categories to existing users, create a migration script:

```python
from app import create_app
from app.extensions import db
from app.expenses.models import Category

app = create_app()
with app.app_context():
    # Add a new category to all users
    users_without_category = db.session.query(User).filter(
        ~User.id.in_(
            db.session.query(Category.user_id)
            .filter(Category.name == "Your New Category")
        )
    ).all()

    for user in users_without_category:
        new_category = Category(
            user_id=user.id,
            name="Your New Category",
            description="Description",
            color="#color",
            icon="icon-name",
            is_default=True
        )
        db.session.add(new_category)

    db.session.commit()
```

## 🎨 **Color and Icon Options**

### **Colors**

Use Bootstrap-compatible hex colors:

- `#fd7e14` - Orange
- `#198754` - Green
- `#0dcaf0` - Cyan
- `#dc3545` - Red
- `#6f42c1` - Purple
- `#0d6efd` - Blue
- `#6c757d` - Gray

### **Icons**

Use Font Awesome icon names (without the `fa-` prefix):

- `utensils` - Fork and knife
- `shopping-cart` - Shopping cart
- `coffee` - Coffee cup
- `hamburger` - Hamburger
- `theater-masks` - Entertainment
- `car` - Transportation
- `question` - Question mark

## 📂 **File Structure**

```
app/
├── constants/
│   ├── __init__.py          # Package exports
│   └── categories.py        # ✅ DEFAULT CATEGORIES DEFINED HERE
├── expenses/
│   └── routes.py           # ✅ Uses centralized categories
├── categories/
│   └── services.py         # ✅ Uses centralized categories
└── init_db.py              # ✅ Fixed - no longer creates categories
```

## 🔄 **Migration from Old System**

If you have existing users with the old category set, you can migrate them:

```python
# Migration script to update existing categories
from app import create_app
from app.extensions import db
from app.expenses.models import Category
from app.constants.categories import get_default_categories

app = create_app()
with app.app_context():
    # Get all users
    users = db.session.query(Category.user_id).distinct().all()

    for (user_id,) in users:
        # Get current categories for user
        current_categories = {c.name for c in Category.query.filter_by(user_id=user_id).all()}

        # Add missing default categories
        for cat_data in get_default_categories():
            if cat_data["name"] not in current_categories:
                new_category = Category(
                    user_id=user_id,
                    name=cat_data["name"],
                    description=cat_data["description"],
                    color=cat_data["color"],
                    icon=cat_data["icon"],
                    is_default=True
                )
                db.session.add(new_category)

    db.session.commit()
    print("Migration completed!")
```

## ✅ **Best Practices**

1. **Test Changes**: Always test category changes in development first
2. **Backup Database**: Create a backup before running migration scripts
3. **User Communication**: Notify users if you're changing their categories
4. **Gradual Rollout**: Consider rolling out category changes gradually
5. **Consistent Naming**: Use clear, consistent category names

## 🚨 **Important Notes**

- **Categories are user-specific** - changes to one user don't affect others
- **Default categories are only applied to new users** unless you run a migration
- **Deleting categories** that have associated expenses may cause data issues
- **Color and icon fields** are optional but recommended for better UX

## 🛠️ **Troubleshooting**

### Problem: Categories not showing up for new users

**Solution**: Check that `_ensure_default_categories_for_user()` is being called in `expenses/routes.py`

### Problem: Old categories still appearing

**Solution**: Categories are user-specific. Run a migration script to update existing users.

### Problem: Database errors when creating categories

**Solution**: Ensure the `color` and `icon` fields exist in your Category model migration.
