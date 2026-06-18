-- =============================================================================
-- 0009_places_nearby.sql
-- Función RPC para búsqueda por proximidad usando earthdistance.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.places_nearby(
    p_lat      DECIMAL,
    p_lng      DECIMAL,
    p_radius_km INTEGER DEFAULT 10,
    p_limit    INTEGER DEFAULT 20
)
RETURNS TABLE (
    id          UUID,
    name        VARCHAR,
    address     TEXT,
    city        VARCHAR,
    partido     VARCHAR,
    lat         DECIMAL,
    lng         DECIMAL,
    phone       VARCHAR,
    website     TEXT,
    instagram   VARCHAR,
    facebook    VARCHAR,
    price_range VARCHAR,
    place_type  VARCHAR,
    has_delivery BOOLEAN,
    payment_methods TEXT[],
    schedule    JSONB,
    menu_highlights TEXT,
    status      VARCHAR,
    avg_rating  DECIMAL,
    review_count INTEGER,
    added_by    UUID,
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ,
    updated_at  TIMESTAMPTZ,
    distance_km DECIMAL
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.*,
        (earth_distance(ll_to_earth(p_lat, p_lng), ll_to_earth(p.lat, p.lng)) / 1000.0)::DECIMAL AS distance_km
    FROM public.burger_places p
    WHERE p.status = 'approved'
      AND earth_box(ll_to_earth(p_lat, p_lng), p_radius_km * 1000) @> ll_to_earth(p.lat, p.lng)
      AND earth_distance(ll_to_earth(p_lat, p_lng), ll_to_earth(p.lat, p.lng)) / 1000.0 <= p_radius_km
    ORDER BY distance_km ASC
    LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION public.places_nearby TO anon, authenticated, service_role;
