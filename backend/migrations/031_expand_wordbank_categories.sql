UPDATE wordbank_categories
SET label = 'Animal', normalized_label = 'animal', updated_at = CURRENT_TIMESTAMP
WHERE normalized_label = 'animals'
  AND NOT EXISTS (SELECT 1 FROM wordbank_categories WHERE normalized_label = 'animal');

UPDATE wordbank_categories
SET label = 'Plant', normalized_label = 'plant', updated_at = CURRENT_TIMESTAMP
WHERE normalized_label = 'plants'
  AND NOT EXISTS (SELECT 1 FROM wordbank_categories WHERE normalized_label = 'plant');

UPDATE wordbank_categories
SET label = 'Drink', normalized_label = 'drink', updated_at = CURRENT_TIMESTAMP
WHERE normalized_label = 'drinks'
  AND NOT EXISTS (SELECT 1 FROM wordbank_categories WHERE normalized_label = 'drink');

UPDATE wordbank_categories
SET label = 'Person', normalized_label = 'person', updated_at = CURRENT_TIMESTAMP
WHERE normalized_label = 'people'
  AND NOT EXISTS (SELECT 1 FROM wordbank_categories WHERE normalized_label = 'person');

UPDATE wordbank_categories
SET label = 'Place', normalized_label = 'place', updated_at = CURRENT_TIMESTAMP
WHERE normalized_label = 'places'
  AND NOT EXISTS (SELECT 1 FROM wordbank_categories WHERE normalized_label = 'place');

UPDATE wordbank_categories
SET label = 'Vehicle', normalized_label = 'vehicle', updated_at = CURRENT_TIMESTAMP
WHERE normalized_label = 'transport'
  AND NOT EXISTS (SELECT 1 FROM wordbank_categories WHERE normalized_label = 'vehicle');

UPDATE wordbank_categories
SET label = 'Emotion', normalized_label = 'emotion', updated_at = CURRENT_TIMESTAMP
WHERE normalized_label = 'emotions'
  AND NOT EXISTS (SELECT 1 FROM wordbank_categories WHERE normalized_label = 'emotion');

UPDATE wordbank_categories
SET label = 'Furniture', normalized_label = 'furniture', updated_at = CURRENT_TIMESTAMP
WHERE normalized_label = 'household objects'
  AND NOT EXISTS (SELECT 1 FROM wordbank_categories WHERE normalized_label = 'furniture');

UPDATE wordbank_categories
SET label = 'Movement', normalized_label = 'movement', updated_at = CURRENT_TIMESTAMP
WHERE normalized_label = 'actions'
  AND NOT EXISTS (SELECT 1 FROM wordbank_categories WHERE normalized_label = 'movement');

INSERT OR IGNORE INTO wordbank_categories (label, normalized_label) VALUES
    ('Animal', 'animal'),
    ('Plant', 'plant'),
    ('Food', 'food'),
    ('Drink', 'drink'),
    ('Family', 'family'),
    ('Person', 'person'),
    ('Body', 'body'),
    ('Clothing', 'clothing'),
    ('Home', 'home'),
    ('Furniture', 'furniture'),
    ('Tool', 'tool'),
    ('Container', 'container'),
    ('Nature', 'nature'),
    ('Weather', 'weather'),
    ('Place', 'place'),
    ('Building', 'building'),
    ('Vehicle', 'vehicle'),
    ('Travel', 'travel'),
    ('Work', 'work'),
    ('School', 'school'),
    ('Learning', 'learning'),
    ('Health', 'health'),
    ('Medicine', 'medicine'),
    ('Time', 'time'),
    ('Emotion', 'emotion'),
    ('Feeling', 'feeling'),
    ('Thought', 'thought'),
    ('Communication', 'communication'),
    ('Movement', 'movement'),
    ('Care', 'care'),
    ('Conflict', 'conflict'),
    ('Relationship', 'relationship'),
    ('Technology', 'technology'),
    ('Money', 'money'),
    ('Law', 'law'),
    ('Art', 'art'),
    ('Music', 'music'),
    ('Sport', 'sport'),
    ('Science', 'science'),
    ('Religion', 'religion'),
    ('Politics', 'politics'),
    ('Grammar', 'grammar'),
    ('Color', 'color'),
    ('Material', 'material'),
    ('Quantity', 'quantity'),
    ('Number', 'number'),
    ('Size', 'size'),
    ('Shape', 'shape'),
    ('Sound', 'sound'),
    ('Light', 'light'),
    ('Water', 'water'),
    ('Fire', 'fire'),
    ('Earth', 'earth'),
    ('Air', 'air'),
    ('Business', 'business'),
    ('Education', 'education'),
    ('Culture', 'culture'),
    ('Community', 'community'),
    ('Media', 'media'),
    ('Writing', 'writing'),
    ('Reading', 'reading'),
    ('Cooking', 'cooking'),
    ('Cleaning', 'cleaning'),
    ('Play', 'play'),
    ('Sleep', 'sleep'),
    ('Creation', 'creation'),
    ('Change', 'change');
