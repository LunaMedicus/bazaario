from datetime import datetime

from .extensions import db
from .models import ALLOWED_CATEGORIES, Category, FarmerProfile, Product, Region, User


DEMO_PASSWORDS = {
    "admin@bazaario.az": "AdminDemo!2026",
    "farmer@bazaario.az": "FarmerDemo!2026",
    "customer@bazaario.az": "CustomerDemo!2026",
}

FARMS = [
    {"key": "goychay_orchard", "name": "Goychay Orchard Cooperative", "region": "Goychay", "email": "farmer@bazaario.az"},
    {"key": "lankaran_citrus", "name": "Caspian Citrus Estate", "region": "Lankaran", "email": "citrus@bazaario.az"},
    {"key": "qabala_highland", "name": "Qabala Highland Garden", "region": "Qabala", "email": "highland@bazaario.az"},
    {"key": "sheki_grain", "name": "Sheki Grain Fields", "region": "Sheki", "email": "grain@bazaario.az"},
    {"key": "astara_tea", "name": "Astara Tea Valley", "region": "Astara", "email": "tea@bazaario.az"},
    {"key": "zagatala_nut", "name": "Zagatala Nut Grove", "region": "Zagatala", "email": "nuts@bazaario.az"},
    {"key": "shamkir_greenhouse", "name": "Shamkir Greenhouse", "region": "Shamkir", "email": "greenhouse@bazaario.az"},
    {"key": "goychay_pomegranate", "name": "Nar Garden Collective", "region": "Goychay", "email": "nar@bazaario.az"},
    {"key": "lankaran_honey", "name": "Lankaran Wildflower Apiary", "region": "Lankaran", "email": "apiary@bazaario.az"},
    {"key": "qabala_dairy", "name": "Qabala Mountain Dairy", "region": "Qabala", "email": "dairy@bazaario.az"},
]

# Wikimedia Commons photographs are direct, hotlinkable media URLs. scripts/check_images.py
# re-fetches every URL before a seed is accepted.
SEED_PRODUCTS = [
    {"farm": "goychay_orchard", "name": "Goychay Red Apples", "category": "Fruit", "price": "4.80", "stock": 80, "season": "August–October", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Apples_in_basket_2018_G2.jpg/1280px-Apples_in_basket_2018_G2.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Crisp red apples picked in the Goychay orchard belt."},
    {"farm": "goychay_orchard", "name": "Golden Delicious Apples", "category": "Fruit", "price": "5.20", "stock": 60, "season": "September–November", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/Golden_Delicious_apples.jpg/1280px-Golden_Delicious_apples.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Honey-sweet golden apples for breakfast and baking."},
    {"farm": "goychay_orchard", "name": "Red Apple Basket", "category": "Fruit", "price": "4.50", "stock": 45, "season": "August–October", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Red_Apple.jpg/1280px-Red_Apple.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "A small-batch basket of orchard-fresh red apples."},
    {"farm": "lankaran_citrus", "name": "Caspian Sweet Oranges", "category": "Fruit", "price": "3.90", "stock": 100, "season": "November–February", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Ambersweet_oranges.jpg/1280px-Ambersweet_oranges.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Bright, juicy oranges from Lankaran's humid coast."},
    {"farm": "lankaran_citrus", "name": "Mandarin Crate", "category": "Fruit", "price": "4.30", "stock": 75, "season": "November–January", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/49/Mandarin_Oranges_%28Citrus_Reticulata%29.jpg/1280px-Mandarin_Oranges_%28Citrus_Reticulata%29.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Easy-peel mandarins with a fragrant citrus finish."},
    {"farm": "lankaran_citrus", "name": "Orange Segments", "category": "Fruit", "price": "4.10", "stock": 48, "season": "December–March", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Orange-Fruit-Pieces.jpg/1280px-Orange-Fruit-Pieces.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Freshly packed citrus segments for sharing."},
    {"farm": "goychay_pomegranate", "name": "Goychay Pomegranate", "category": "Fruit", "price": "6.80", "stock": 70, "season": "September–December", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Pomegranate02_edit.jpg/1280px-Pomegranate02_edit.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Ruby arils from Azerbaijan's best-known pomegranate region."},
    {"farm": "goychay_pomegranate", "name": "Pomegranate Duo", "category": "Fruit", "price": "7.20", "stock": 50, "season": "October–December", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Pomegranate03_edit.jpg/1280px-Pomegranate03_edit.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Two full pomegranates, selected for deep colour and juice."},
    {"farm": "qabala_highland", "name": "Mountain Peaches", "category": "Fruit", "price": "5.80", "stock": 38, "season": "July–August", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Autumn_Red_peaches.jpg/1280px-Autumn_Red_peaches.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "A fragrant summer peach crop from Qabala's foothills."},
    {"farm": "qabala_highland", "name": "Sheki-Road Peaches", "category": "Fruit", "price": "5.50", "stock": 32, "season": "July–September", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Peach_fruit_3.jpg/1280px-Peach_fruit_3.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Soft, ripe peaches harvested at the weekend market window."},
    {"farm": "shamkir_greenhouse", "name": "Shamkir Vine Tomatoes", "category": "Vegetables", "price": "3.60", "stock": 90, "season": "May–October", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/88/Bright_red_tomato_and_cross_section02.jpg/1280px-Bright_red_tomato_and_cross_section02.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Sun-ripened tomatoes with a clean, savoury bite."},
    {"farm": "shamkir_greenhouse", "name": "Organic Tomato Mix", "category": "Vegetables", "price": "4.10", "stock": 65, "season": "April–November", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Organic_home-grown_tomatoes_-_unripe_to_ripe.jpg/1280px-Organic_home-grown_tomatoes_-_unripe_to_ripe.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "A colourful mix picked as each tomato reaches its best stage."},
    {"farm": "shamkir_greenhouse", "name": "Tomato Salad Pair", "category": "Vegetables", "price": "3.80", "stock": 55, "season": "May–October", "image_url": "https://upload.wikimedia.org/wikipedia/commons/d/d2/Tomatoes_plain_and_sliced.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail_unscaled", "description": "Firm salad tomatoes for a two-day kitchen supply."},
    {"farm": "lankaran_citrus", "name": "Lankaran Cucumbers", "category": "Vegetables", "price": "2.90", "stock": 110, "season": "April–September", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0e/Harvested_vegetables%28Cucumbers%29.jpg/1280px-Harvested_vegetables%28Cucumbers%29.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Cool, crunchy cucumbers from the coastal growing season."},
    {"farm": "shamkir_greenhouse", "name": "Market Cucumbers", "category": "Vegetables", "price": "2.70", "stock": 95, "season": "May–September", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Kurkkuja.jpg/1280px-Kurkkuja.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Freshly harvested cucumbers with a delicate skin."},
    {"farm": "sheki_grain", "name": "Sheki Table Potatoes", "category": "Vegetables", "price": "1.90", "stock": 140, "season": "June–October", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1f/Food-healthy-vegetables-potatoes_%2823958160949%29.jpg/1280px-Food-healthy-vegetables-potatoes_%2823958160949%29.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Earthy, versatile potatoes from the Sheki uplands."},
    {"farm": "sheki_grain", "name": "Garden-Grown Eggplant", "category": "Vegetables", "price": "3.20", "stock": 64, "season": "June–September", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/3_x_Small_eggplant_2017_D.jpg/1280px-3_x_Small_eggplant_2017_D.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Glossy eggplant for grilling, stews and dolma."},
    {"farm": "sheki_grain", "name": "Sheki Wheat Grain", "category": "Grains", "price": "2.40", "stock": 180, "season": "July–September", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Wheat_close-up.JPG/1280px-Wheat_close-up.JPG?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Clean, locally grown wheat grain sold by the kilogram."},
    {"farm": "sheki_grain", "name": "Golden Field Wheat", "category": "Grains", "price": "2.20", "stock": 220, "season": "July–August", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/Sunset-over-the-wheat-field-featured.jpg/1280px-Sunset-over-the-wheat-field-featured.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "A pantry staple from a small family grain field."},
    {"farm": "sheki_grain", "name": "IRRI Rice Grains", "category": "Grains", "price": "3.70", "stock": 125, "season": "All year", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/ba/Rice_grains_%28IRRI%29.jpg/1280px-Rice_grains_%28IRRI%29.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Long, clean rice grains for everyday cooking."},
    {"farm": "sheki_grain", "name": "Long Grain Rice", "category": "Grains", "price": "3.90", "stock": 115, "season": "All year", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e9/U.S._long_grain_rice_K7577-1.jpg/1280px-U.S._long_grain_rice_K7577-1.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Separate, fluffy grains for pilaf and family meals."},
    {"farm": "qabala_dairy", "name": "Qabala Goat Cheese", "category": "Dairy", "price": "12.50", "stock": 28, "season": "All year", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b6/Goat_cheese_%284804052501%29.jpg/1280px-Goat_cheese_%284804052501%29.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Tangy, soft goat cheese made in small mountain batches."},
    {"farm": "qabala_dairy", "name": "Crottin Mountain Cheese", "category": "Dairy", "price": "14.00", "stock": 20, "season": "All year", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Crottin_02.jpg/1280px-Crottin_02.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "A compact aged cheese with a gentle, nutty finish."},
    {"farm": "qabala_dairy", "name": "Farmhouse Cheese Board", "category": "Dairy", "price": "18.50", "stock": 16, "season": "All year", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/USDA_Commodities_Cheeses.jpg/1280px-USDA_Commodities_Cheeses.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "A varied selection of farm cheeses for a weekend table."},
    {"farm": "qabala_dairy", "name": "Meltable Village Cheese", "category": "Dairy", "price": "10.80", "stock": 34, "season": "All year", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/Processed_cheese.jpg/1280px-Processed_cheese.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Smooth, mild cheese for toasties and warm dishes."},
    {"farm": "lankaran_honey", "name": "Wildflower Honey Jar", "category": "Honey & bee products", "price": "16.00", "stock": 42, "season": "May–September", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/34/Dipper_stick_and_honey_in_a_jar.jpg/1280px-Dipper_stick_and_honey_in_a_jar.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Raw wildflower honey gathered around Lankaran meadows."},
    {"farm": "lankaran_honey", "name": "Creamed Honey", "category": "Honey & bee products", "price": "18.00", "stock": 30, "season": "All year", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/88/Selection_of_creamed_honey_jars_from_Europe.jpg/1280px-Selection_of_creamed_honey_jars_from_Europe.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Silky creamed honey with a slow, floral sweetness."},
    {"farm": "lankaran_honey", "name": "Monofloral Honey Trio", "category": "Honey & bee products", "price": "27.00", "stock": 18, "season": "All year", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/24/Three_French_monofloral_honey_jars.jpg/1280px-Three_French_monofloral_honey_jars.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Three floral profiles to taste across the season."},
    {"farm": "lankaran_honey", "name": "Bee Meadow Honey", "category": "Honey & bee products", "price": "14.50", "stock": 36, "season": "May–August", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/European_honey_bee_extracts_nectar.jpg/1280px-European_honey_bee_extracts_nectar.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "A fragrant jar from hives placed beside flowering fields."},
    {"farm": "astara_tea", "name": "Fresh Mint Bunch", "category": "Herbs", "price": "2.50", "stock": 70, "season": "May–October", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/Fresh_Mint_leaves.jpg/1280px-Fresh_Mint_leaves.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Cool, aromatic mint cut to order."},
    {"farm": "astara_tea", "name": "Garden Basil", "category": "Herbs", "price": "3.00", "stock": 54, "season": "May–September", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Basil-Basilico-Ocimum_basilicum-albahaca.jpg/1280px-Basil-Basilico-Ocimum_basilicum-albahaca.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Fragrant basil for salads, sauces and fresh bread."},
    {"farm": "astara_tea", "name": "Potted Mint Plant", "category": "Herbs", "price": "7.50", "stock": 24, "season": "April–September", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/81/Mint_plant_in_water.jpg/1280px-Mint_plant_in_water.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "A living mint plant for the kitchen windowsill."},
    {"farm": "astara_tea", "name": "Kitchen Herb Mix", "category": "Herbs", "price": "5.80", "stock": 30, "season": "May–October", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Herb_garden_or_flowerbed_-_edible_plants_for_cooking.jpg/1280px-Herb_garden_or_flowerbed_-_edible_plants_for_cooking.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "A seasonal mix of edible leaves for everyday cooking."},
    {"farm": "zagatala_nut", "name": "Zagatala Hazelnuts", "category": "Nuts", "price": "19.00", "stock": 50, "season": "September–November", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Hazelnuts.jpg/1280px-Hazelnuts.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Roast-ready hazelnuts from Zagatala's nut groves."},
    {"farm": "zagatala_nut", "name": "Walnut & Hazelnut Table Mix", "category": "Nuts", "price": "22.00", "stock": 38, "season": "September–December", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Pecans%2C_hazelnuts%2C_walnuts%2C_almonds%2C_Brazil_nuts_on_a_table_with_logs_1.jpg/1280px-Pecans%2C_hazelnuts%2C_walnuts%2C_almonds%2C_Brazil_nuts_on_a_table_with_logs_1.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "A generous mix of local nuts for baking or snacking."},
    {"farm": "zagatala_nut", "name": "Orchard Nut Selection", "category": "Nuts", "price": "24.50", "stock": 32, "season": "October–January", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/Pecans%2C_hazelnuts%2C_walnuts%2C_almonds%2C_Brazil_nuts_on_a_table_with_logs_3.jpg/1280px-Pecans%2C_hazelnuts%2C_walnuts%2C_almonds%2C_Brazil_nuts_on_a_table_with_logs_3.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Whole nuts selected for a crisp bite and rich aroma."},
    {"farm": "zagatala_nut", "name": "Almond & Raisin Mix", "category": "Nuts", "price": "17.50", "stock": 42, "season": "All year", "image_url": "https://upload.wikimedia.org/wikipedia/commons/1/1f/Cut_almonds%2C_cut_cashews_and_raisins.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail_unscaled", "description": "A ready-to-share almond, cashew and raisin snack mix."},
    {"farm": "astara_tea", "name": "Astara Green Tea", "category": "Tea", "price": "13.50", "stock": 55, "season": "May–July", "image_url": "https://upload.wikimedia.org/wikipedia/commons/5/54/Dried_jakseol_green_tea_leaves.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail_unscaled", "description": "Hand-processed green tea with a clean coastal aroma."},
    {"farm": "astara_tea", "name": "Young Tea Leaves", "category": "Tea", "price": "15.00", "stock": 40, "season": "May–July", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/81/Green_tea_leaves_and_a_cloudy_sky_01.jpg/1280px-Green_tea_leaves_and_a_cloudy_sky_01.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "Tender leaves harvested early for a lighter cup."},
    {"farm": "astara_tea", "name": "Cloud Valley Tea Leaves", "category": "Tea", "price": "14.20", "stock": 46, "season": "May–August", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/Green_tea_leaves_and_a_cloudy_sky_02.jpg/1280px-Green_tea_leaves_and_a_cloudy_sky_02.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "A fragrant loose-leaf tea from misty Astara slopes."},
    {"farm": "astara_tea", "name": "Jade Tea Selection", "category": "Tea", "price": "16.50", "stock": 35, "season": "May–August", "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Zhu-Ye-Qing-Tea-03.jpg/1280px-Zhu-Ye-Qing-Tea-03.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=thumbnail", "description": "A bright green tea selection for slow afternoon brewing."},
]


def seed_database():
    db.drop_all()
    db.create_all()

    for name in ALLOWED_CATEGORIES:
        db.session.add(Category(name=name))
    for region in sorted({farm["region"] for farm in FARMS}):
        db.session.add(Region(name=region))

    admin = User(email="admin@bazaario.az", display_name="Bazaario Admin", role="admin")
    admin.set_password(DEMO_PASSWORDS[admin.email])
    db.session.add(admin)

    users_by_key = {}
    for farm in FARMS:
        user = User(email=farm["email"], display_name=farm["name"], role="farmer")
        user.set_password(DEMO_PASSWORDS.get(farm["email"], "FarmerDemo!2026"))
        db.session.add(user)
        db.session.flush()
        db.session.add(
            FarmerProfile(
                user_id=user.id,
                farm_name=farm["name"],
                region=farm["region"],
                document_reference=f"AZ-FARM-{user.id:04d}",
                verification_status="approved",
                verified_at=datetime.utcnow(),
            )
        )
        users_by_key[farm["key"]] = user

    customer = User(email="customer@bazaario.az", display_name="Demo Customer", role="customer")
    customer.set_password(DEMO_PASSWORDS[customer.email])
    db.session.add(customer)

    for row in SEED_PRODUCTS:
        db.session.add(
            Product(
                farmer_id=users_by_key[row["farm"]].id,
                name=row["name"],
                category=row["category"],
                price_azn=row["price"],
                stock=row["stock"],
                season=row["season"],
                image_url=row["image_url"],
                description=row["description"],
            )
        )
    db.session.commit()
    return {"farms": len(FARMS), "products": len(SEED_PRODUCTS), "categories": len(ALLOWED_CATEGORIES)}
