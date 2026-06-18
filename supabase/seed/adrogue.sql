-- =============================================================================
-- supabase/seed/adrogue.sql
-- 12 locales mockeados en Adrogué + partidos cercanos + reviews
-- =============================================================================
-- IMPORTANTE: solo correr DESPUÉS de las migraciones 0001-0009.
-- En Supabase local: supabase db reset
-- En Supabase cloud: pegar este archivo en SQL Editor

-- ====================== LIMPIAR DATA PREVIA ======================
TRUNCATE public.reviews, public.photos, public.edit_suggestions, public.burger_places
RESTART IDENTITY CASCADE;

-- ====================== USUARIO MOCK (admin) ======================
-- Este user_id se usa para "added_by" y "approved_by".
-- Reemplazá por el UUID real de tu usuario admin después.
-- Si no lo tenés, simplemente dejá que los NULLs sean null.
DO $$
DECLARE
    admin_id UUID;
    user1_id UUID := '11111111-1111-1111-1111-111111111111';
    user2_id UUID := '22222222-2222-2222-2222-222222222222';
    user3_id UUID := '33333333-3333-3333-3333-333333333333';
    user4_id UUID := '44444444-4444-4444-4444-444444444444';
    place_ids UUID[] := ARRAY[]::UUID[];
    pid UUID;
BEGIN

-- ====================== LOCALES ======================
INSERT INTO public.burger_places (
    name, address, city, partido, lat, lng, phone, website, instagram,
    price_range, place_type, has_delivery, payment_methods, schedule,
    menu_highlights, status, avg_rating, review_count, approved_at
) VALUES

-- 1
('Burger Adrogué', 'Av. Hipólito Yrigoyen 12500, Adrogué', 'Adrogué', 'Almirante Brown',
 -34.8003, -58.3856, '+5491155551001', 'https://burgeradrogue.com', 'burgeradrogue',
 'mid', 'gourmet', true,
 ARRAY['efectivo', 'debito', 'credito', 'mp'],
 '{"lun":"Cerrado","mar":"19:00-00:00","mie":"19:00-00:00","jue":"19:00-00:30","vie":"19:00-01:00","sab":"19:00-01:30","dom":"19:00-00:00"}',
 'Smash burger de 180g con queso cheddar y panceta ahumada',
 'approved', 0, 0, NOW())
RETURNING id INTO pid; place_ids := array_append(place_ids, pid);

-- 2
('La Birra Bar', 'Av. Espora 850, Adrogué', 'Adrogué', 'Almirante Brown',
 -34.8025, -58.3891, '+5491155551002', NULL, 'labirra.adrogue',
 'expensive', 'gourmet', true,
 ARRAY['efectivo', 'debito', 'credito', 'mp', 'uala'],
 '{"lun":"Cerrado","mar":"20:00-01:00","mie":"20:00-01:00","jue":"20:00-01:00","vie":"20:00-02:00","sab":"20:00-02:00","dom":"20:00-01:00"}',
 'Hamburguesa de búfalo con rúcula y alioli',
 'approved', 0, 0, NOW())
RETURNING id INTO pid; place_ids := array_append(place_ids, pid);

-- 3
('Patio Burger', 'Mitre 1450, Adrogué', 'Adrogué', 'Almirante Brown',
 -34.8045, -58.3871, '+5491155551003', NULL, 'patioburger',
 'mid', 'gourmet', true,
 ARRAY['efectivo', 'debito', 'mp'],
 '{"lun":"12:00-15:00, 19:00-00:00","mar":"12:00-15:00, 19:00-00:00","mie":"12:00-15:00, 19:00-00:00","jue":"12:00-15:00, 19:00-00:00","vie":"12:00-15:00, 19:00-01:00","sab":"19:00-01:00","dom":"Cerrado"}',
 'Papas cheddar bacon + burgers de la casa',
 'approved', 0, 0, NOW())
RETURNING id INTO pid; place_ids := array_append(place_ids, pid);

-- 4
('McBurger Express', 'Av. Yrigoyen 13000, Adrogué', 'Adrogué', 'Almirante Brown',
 -34.7989, -58.3801, '+5491155551004', NULL, NULL,
 'cheap', 'fast_food', true,
 ARRAY['efectivo', 'debito', 'credito', 'mp'],
 '{"lun":"11:00-01:00","mar":"11:00-01:00","mie":"11:00-01:00","jue":"11:00-01:00","vie":"11:00-03:00","sab":"11:00-03:00","dom":"11:00-01:00"}',
 'Combos a precio deCombos a precio de crisis, doble queso',
 'approved', 0, 0, NOW())
RETURNING id INTO pid; place_ids := array_append(place_ids, pid);

-- 5
('Burger Truck Zona Sur', 'Plaza Brown, Adrogué', 'Adrogué', 'Almirante Brown',
 -34.8021, -58.3856, '+5491155551005', NULL, 'burgertruck.zs',
 'mid', 'food_truck', false,
 ARRAY['efectivo', 'mp', 'uala'],
 '{"jue":"19:00-00:00","vie":"19:00-01:00","sab":"19:00-02:00","dom":"19:00-00:00"}',
 'Truco de la semana: burger de cordero braseado',
 'approved', 0, 0, NOW())
RETURNING id INTO pid; place_ids := array_append(place_ids, pid);

-- 6
('Dark Kitchen Adrogué', 'Solo delivery, Adrogué', 'Adrogué', 'Almirante Brown',
 -34.8050, -58.3870, '+5491155551006', 'https://darkadrogue.com', 'darkadrogue',
 'mid', 'dark_kitchen', true,
 ARRAY['mp', 'uala', 'credito'],
 '{"lun":"20:00-00:00","mar":"20:00-00:00","mie":"20:00-00:00","jue":"20:00-00:00","vie":"20:00-01:00","sab":"20:00-01:00","dom":"20:00-00:00"}',
 '4 estilos distintos en un mismo pedido, delivery en 30min',
 'approved', 0, 0, NOW())
RETURNING id INTO pid; place_ids := array_append(place_ids, pid);

-- 7
('La Esquina Burger', 'Av. San Martín 2200, Adrogué', 'Adrogué', 'Almirante Brown',
 -34.8061, -58.3901, '+5491155551007', NULL, 'laesquina.burger',
 'cheap', 'fast_food', true,
 ARRAY['efectivo'],
 '{"lun":"19:00-00:00","mar":"19:00-00:00","mie":"Cerrado","jue":"19:00-00:00","vie":"19:00-02:00","sab":"19:00-02:00","dom":"19:00-00:00"}',
 'Lomito completo + papas fritas',
 'approved', 0, 0, NOW())
RETURNING id INTO pid; place_ids := array_append(place_ids, pid);

-- 8
('Cervecería Burro', 'Belgrano 1200, Adrogué', 'Adrogué', 'Almirante Brown',
 -34.8015, -58.3850, '+5491155551008', 'https://cerveceriaburro.com', 'cerveceriaburro',
 'expensive', 'gourmet', false,
 ARRAY['efectivo', 'debito', 'credito', 'mp'],
 '{"mar":"19:00-01:00","mie":"19:00-01:00","jue":"19:00-01:00","vie":"19:00-02:30","sab":"12:00-15:00, 19:00-02:30","dom":"12:00-15:00"}',
 'IPA artesanal + burger de la casa con queso azul',
 'approved', 0, 0, NOW())
RETURNING id INTO pid; place_ids := array_append(place_ids, pid);

-- 9
('Burger Lanús', 'Av. Hipólito Yrigoyen 4200, Lanús', 'Lanús', 'Lanús',
 -34.7075, -58.3920, '+5491155551009', NULL, 'burger.lanus',
 'mid', 'gourmet', true,
 ARRAY['efectivo', 'debito', 'mp'],
 '{"lun":"Cerrado","mar":"19:30-00:00","mie":"19:30-00:00","jue":"19:30-00:00","vie":"19:30-01:00","sab":"19:30-01:30","dom":"19:30-00:00"}',
 'Burger de ossobuco braseado 8hs',
 'approved', 0, 0, NOW())
RETURNING id INTO pid; place_ids := array_append(place_ids, pid);

-- 10
('Lomitos del Sur', 'Av. Mitre 3500, Lanús', 'Lanús', 'Lanús',
 -34.7110, -58.3880, '+5491155551010', NULL, NULL,
 'cheap', 'fast_food', true,
 ARRAY['efectivo'],
 '{"lun":"19:00-00:00","mar":"19:00-00:00","mie":"19:00-00:00","jue":"19:00-00:00","vie":"19:00-01:30","sab":"19:00-01:30","dom":"Cerrado"}',
 'Lomitos XL con papas',
 'approved', 0, 0, NOW())
RETURNING id INTO pid; place_ids := array_append(place_ids, pid);

-- 11
('Burger Banfield', 'Av. Alem 1500, Banfield', 'Banfield', 'Lomas de Zamora',
 -34.7440, -58.3985, '+5491155551011', 'https://burgerbanfield.com', 'burgerbanfield',
 'mid', 'gourmet', true,
 ARRAY['efectivo', 'debito', 'credito', 'mp'],
 '{"lun":"Cerrado","mar":"19:00-00:00","mie":"19:00-00:00","jue":"19:00-00:00","vie":"19:00-01:30","sab":"19:00-01:30","dom":"19:00-00:00"}',
 'Burger de wagyu argentino + papas trufadas',
 'approved', 0, 0, NOW())
RETURNING id INTO pid; place_ids := array_append(place_ids, pid);

-- 12
('Burger Lomas', 'Av. Meeks 850, Lomas de Zamora', 'Lomas de Zamora', 'Lomas de Zamora',
 -34.7610, -58.4025, '+5491155551012', NULL, 'burger.lomas',
 'cheap', 'fast_food', true,
 ARRAY['efectivo', 'mp'],
 '{"lun":"11:00-23:00","mar":"11:00-23:00","mie":"11:00-23:00","jue":"11:00-23:00","vie":"11:00-02:00","sab":"11:00-02:00","dom":"11:00-23:00"}',
 'Hamburguesa simple bien hecha, sin vueltas',
 'approved', 0, 0, NOW())
RETURNING id INTO pid; place_ids := array_append(place_ids, pid);

-- ====================== REVIEWS ======================
-- 3 reviews por local, distribuidas en los últimos 14 días.
-- (Usamos los user_ids ficticios que NO están en auth.users,
-- por eso usamos disable trigger o los creamos primero)
-- Para no romper FK, primero creamos los profiles:

INSERT INTO public.profiles (id, name, role, is_active) VALUES
    (user1_id, 'Juan Pérez', 'user', true),
    (user2_id, 'María López', 'user', true),
    (user3_id, 'Carlos Gómez', 'user', true),
    (user4_id, 'Ana Martínez', 'admin', true)
ON CONFLICT (id) DO NOTHING;

-- Reviews (una sola por usuario por local, por la constraint UNIQUE)
INSERT INTO public.reviews (place_id, user_id, rating, comment, created_at)
SELECT
    pid,
    CASE (i % 4)
        WHEN 0 THEN user1_id
        WHEN 1 THEN user2_id
        WHEN 2 THEN user3_id
        WHEN 3 THEN user4_id
    END,
    (3 + (i % 3))::int,  -- ratings 3, 4 o 5
    CASE (i % 5)
        WHEN 0 THEN 'Excelente burger, muy bien servida y el lugar está buenísimo.'
        WHEN 1 THEN 'Buen sabor pero tardó bastante el delivery.'
        WHEN 2 THEN 'Volveré! El pan es espectacular.'
        WHEN 3 THEN 'Relación precio-calidad muy buena.'
        WHEN 4 THEN 'Las papas son un golazo, la burger podría tener más queso.'
    END,
    NOW() - ((i * 1.2)::int || ' days')::interval
FROM (
    SELECT place_ids[i] AS pid, generate_series(1, array_length(place_ids, 1)) AS i
    FROM generate_series(1, 12) AS i
) sub,
generate_series(1, 3) AS r(i)
CROSS JOIN LATERAL (
    SELECT pid FROM unnest(place_ids) WITH ORDINALITY AS u(pid, ord) WHERE ord = r.i
) src;

-- Como hay 12 lugares y queremos 3 reviews por lugar (36 reviews),
-- repetimos usuarios por local (la UNIQUE es (place_id, user_id)):
INSERT INTO public.reviews (place_id, user_id, rating, comment, created_at)
SELECT
    place_ids[i],
    CASE ((i + r) % 4)
        WHEN 0 THEN user1_id
        WHEN 1 THEN user2_id
        WHEN 2 THEN user3_id
        WHEN 3 THEN user4_id
    END,
    (3 + ((i + r) % 3))::int,
    CASE ((i + r) % 5)
        WHEN 0 THEN 'Pedí 2 veces en 1 semana, no defrauda.'
        WHEN 1 THEN 'Probé la nueva burger del mes, muy buena.'
        WHEN 2 THEN 'El ambiente es muy lindo, ideal para ir con amigos.'
        WHEN 3 THEN 'Atención 10 puntos, los recomiendo.'
        WHEN 4 THEN 'Buen precio, sabor correcto. Nada memorable pero cumple.'
    END,
    NOW() - (((i * 1.2) + (r * 0.5))::int || ' days')::interval
FROM generate_series(1, 12) AS i
CROSS JOIN generate_series(1, 3) AS r;

END $$;
