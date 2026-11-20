from dataclasses import dataclass


@dataclass(frozen=True)
class Sample:
    name: str
    cuisine: str
    photo: str
    rating: float
    price: int
    vegetarian: bool


SAMPLES = tuple(Sample(*row) for row in (
    ("Banana Leaf Kitchen", "South Indian", "dosa", 4.7, 350, True),
    ("Copper Pot Biryani", "Biryani", "biryani", 4.6, 450, False),
    ("Little Napoli", "Pizza", "pizza", 4.5, 650, False),
    ("The Filter Coffee Club", "Cafe", "cafe", 4.8, 300, True),
    ("Coriander House", "North Indian", "indian", 4.4, 550, False),
    ("Wok & Steam", "Chinese", "asian", 4.5, 500, False),
    ("Saffron Table", "Indian", "indian", 4.6, 700, True),
    ("Pasta Courtyard", "Italian", "italian", 4.3, 750, False),
    ("Tamarind Tiffins", "South Indian", "dosa", 4.6, 220, True),
    ("Golden Dum", "Biryani", "biryani", 4.4, 500, False),
    ("Lotus Bowl", "Asian", "asian", 4.5, 600, True),
    ("Sunday Dough", "Pizza", "pizza", 4.8, 650, True),
    ("The Cardamom Cafe", "Cafe", "cafe", 4.5, 480, False),
    ("Mustard Seed Bhoj", "Indian", "indian", 4.3, 280, True),
    ("Jasmine & Rice", "Asian", "asian", 4.2, 820, False),
    ("Black Clay Tandoor", "North Indian", "indian", 4.7, 860, False),
    ("Red Lantern Noodles", "Chinese", "asian", 4.1, 320, False),
    ("Garden Oven", "Italian", "italian", 4.6, 700, True),
    ("Palm Grove Meals", "South Indian", "dosa", 4.4, 420, False),
    ("Turmeric Thali", "North Indian", "indian", 4.8, 550, True),
    ("Brickhouse Slice", "Pizza", "pizza", 4.3, 850, False),
    ("Blue Fig Bakery", "Cafe", "cafe", 4.6, 420, True),
    ("Basil & Olive", "Italian", "italian", 4.5, 1000, False),
    ("White Pepper Mess", "Biryani", "biryani", 4.6, 330, False),
    ("Monsoon Chaat House", "Indian", "indian", 4.4, 200, True),
    ("Plum Blossom Kitchen", "Chinese", "asian", 4.6, 550, True),
    ("Koji Corner", "Asian", "asian", 4.7, 1200, False),
    ("Udupi Breakfast Room", "South Indian", "dosa", 4.5, 180, True),
    ("Mango Tree Canteen", "Indian", "indian", 4.2, 370, False),
    ("Mitti & Makhani", "North Indian", "indian", 4.6, 470, True),
    ("Camellia Coffee Bar", "Cafe", "cafe", 4.4, 590, False),
    ("Hyderabad Spice Co.", "Biryani", "biryani", 4.7, 620, False),
    ("Eight Spice Wok", "Chinese", "asian", 4.3, 450, False),
    ("Dosa & Co.", "South Indian", "dosa", 4.5, 260, True),
    ("Rice Paper Social", "Asian", "asian", 4.6, 730, False),
    ("Second Rise Pizzeria", "Pizza", "pizza", 4.7, 780, True),
))
