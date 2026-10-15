"""
AutoCart Location & Geospatial Fulfillment Service.
Provides Haversine distance calculation, city/PIN geocoding fallback,
serviceability radius filtering, and nearby store inventory lookup.
"""

import math
from typing import Dict, List, Any, Optional, Tuple
from django.db.models import Q
from .models import Store, StoreInventory, Product

# The 10 Primary Hyperlocal Operating Zones across Mumbai & MMR
MUMBAI_ZONES = {
    'thane': {
        'id': 'thane',
        'name': 'Thane',
        'lat': 19.2183,
        'lng': 72.9781,
        'pincodes': ['400601', '400602', '400604', '400606', '400607'],
        'description': 'Viviana Mall, Naupada, Hiranandani Estate, Teen Hath Naka'
    },
    'kalyan': {
        'id': 'kalyan',
        'name': 'Kalyan',
        'lat': 19.2403,
        'lng': 73.1305,
        'pincodes': ['421301', '421304', '421306'],
        'description': 'Khadakpada, Station Road, Wayle Nagar, Birla College, Kolsewadi'
    },
    'dombivli': {
        'id': 'dombivli',
        'name': 'Dombivli',
        'lat': 19.2184,
        'lng': 73.0867,
        'pincodes': ['421201', '421202', '421204'],
        'description': 'Phadke Road, Manpada, Lodha Palava, Tilak Road, Gupte Road'
    },
    'mulund': {
        'id': 'mulund',
        'name': 'Mulund',
        'lat': 19.1726,
        'lng': 72.9565,
        'pincodes': ['400080', '400081'],
        'description': 'MG Road, R Mall, Sarvodaya Nagar, Mithagar, Yogi Hills, Nahur'
    },
    'bhandup': {
        'id': 'bhandup',
        'name': 'Bhandup',
        'lat': 19.1458,
        'lng': 72.9372,
        'pincodes': ['400078'],
        'description': 'Dreams Mall, LBS Marg, Station Road, Usha Nagar, Kanjur Link'
    },
    'ghatkopar': {
        'id': 'ghatkopar',
        'name': 'Ghatkopar',
        'lat': 19.0860,
        'lng': 72.9090,
        'pincodes': ['400077', '400086', '400075'],
        'description': 'R City Mall, Vallabh Baug, Pant Nagar, Amrut Nagar, MG Road'
    },
    'powai': {
        'id': 'powai',
        'name': 'Powai',
        'lat': 19.1176,
        'lng': 72.9060,
        'pincodes': ['400076', '400072'],
        'description': 'Hiranandani Gardens, Galleria, IIT Bombay, Chandivali, Saki Vihar'
    },
    'andheri': {
        'id': 'andheri',
        'name': 'Andheri',
        'lat': 19.1136,
        'lng': 72.8697,
        'pincodes': ['400053', '400058', '400069', '400059', '400093'],
        'description': 'Lokhandwala, Chakala, Infinity Mall, JB Nagar, MIDC, Marol'
    },
    'borivali': {
        'id': 'borivali',
        'name': 'Borivali',
        'lat': 19.2307,
        'lng': 72.8567,
        'pincodes': ['400091', '400092', '400066', '400103'],
        'description': 'Shimpoli, IC Colony, SV Road, Carter Road, Chikuwadi, National Park'
    },
    'navi mumbai': {
        'id': 'navi mumbai',
        'name': 'Navi Mumbai',
        'lat': 19.0330,
        'lng': 73.0297,
        'pincodes': ['400703', '400705', '400706', '400614', '410210'],
        'description': 'Vashi Sector 17, Seawoods Grand Central, Palm Beach, Nerul, Belapur, Kharghar'
    }
}

# Approximate coordinates for key Indian logistics hubs & metro districts
KNOWN_GEOCODING_DATABASE = {
    # 1. Thane
    '400606': {'city': 'Thane', 'area': 'Viviana Mall / Vartak Nagar', 'lat': 19.2085, 'lng': 72.9716},
    '400602': {'city': 'Thane', 'area': 'Naupada / Station', 'lat': 19.1895, 'lng': 72.9723},
    '400607': {'city': 'Thane', 'area': 'Hiranandani Estate / Ghodbunder', 'lat': 19.2558, 'lng': 72.9806},
    '400601': {'city': 'Thane', 'area': 'Majiwada Junction', 'lat': 19.2140, 'lng': 72.9870},
    '400604': {'city': 'Thane', 'area': 'Teen Hath Naka', 'lat': 19.1862, 'lng': 72.9598},
    'thane': {'city': 'Thane', 'area': 'Central Thane', 'lat': 19.2183, 'lng': 72.9781},

    # 2. Kalyan
    '421301': {'city': 'Kalyan', 'area': 'Khadakpada / Station Road', 'lat': 19.2551, 'lng': 73.1378},
    '421304': {'city': 'Kalyan', 'area': 'Gandhinagar / Kalyan West', 'lat': 19.2450, 'lng': 73.1300},
    '421306': {'city': 'Kalyan', 'area': 'Kolsewadi / Kalyan East', 'lat': 19.2295, 'lng': 73.1410},
    'kalyan': {'city': 'Kalyan', 'area': 'Central Kalyan', 'lat': 19.2403, 'lng': 73.1305},

    # 3. Dombivli
    '421201': {'city': 'Dombivli', 'area': 'Phadke Road / Manpada', 'lat': 19.2165, 'lng': 73.0872},
    '421202': {'city': 'Dombivli', 'area': 'Gupte Road / Dombivli West', 'lat': 19.2190, 'lng': 73.0785},
    '421204': {'city': 'Dombivli', 'area': 'Lodha Palava / Xperia Mall', 'lat': 19.1915, 'lng': 73.0780},
    'dombivli': {'city': 'Dombivli', 'area': 'Central Dombivli', 'lat': 19.2184, 'lng': 73.0867},
    'dombivali': {'city': 'Dombivli', 'area': 'Central Dombivli', 'lat': 19.2184, 'lng': 73.0867},

    # 4. Mulund
    '400080': {'city': 'Mulund', 'area': 'MG Road / R Mall / Mulund West', 'lat': 19.1735, 'lng': 72.9530},
    '400081': {'city': 'Mulund', 'area': 'Mithagar / Mulund East', 'lat': 19.1685, 'lng': 72.9660},
    'mulund': {'city': 'Mulund', 'area': 'Central Mulund', 'lat': 19.1726, 'lng': 72.9565},

    # 5. Bhandup
    '400078': {'city': 'Bhandup', 'area': 'Dreams Mall / LBS Marg / Station', 'lat': 19.1458, 'lng': 72.9372},
    'bhandup': {'city': 'Bhandup', 'area': 'Central Bhandup', 'lat': 19.1458, 'lng': 72.9372},

    # 6. Ghatkopar
    '400086': {'city': 'Ghatkopar', 'area': 'R City Mall / LBS Marg', 'lat': 19.0990, 'lng': 72.9165},
    '400077': {'city': 'Ghatkopar', 'area': 'Vallabh Baug / Ghatkopar East', 'lat': 19.0815, 'lng': 72.9080},
    '400075': {'city': 'Ghatkopar', 'area': 'Pant Nagar', 'lat': 19.0780, 'lng': 72.9150},
    'ghatkopar': {'city': 'Ghatkopar', 'area': 'Central Ghatkopar', 'lat': 19.0860, 'lng': 72.9090},

    # 7. Powai
    '400076': {'city': 'Powai', 'area': 'Hiranandani Gardens / Galleria', 'lat': 19.1195, 'lng': 72.9085},
    '400072': {'city': 'Powai', 'area': 'Chandivali / Saki Vihar Road', 'lat': 19.1120, 'lng': 72.8960},
    'powai': {'city': 'Powai', 'area': 'Central Powai', 'lat': 19.1176, 'lng': 72.9060},

    # 8. Andheri
    '400053': {'city': 'Andheri', 'area': 'Lokhandwala Complex / Andheri West', 'lat': 19.1410, 'lng': 72.8285},
    '400069': {'city': 'Andheri', 'area': 'Chakala / Andheri East', 'lat': 19.1136, 'lng': 72.8697},
    '400059': {'city': 'Andheri', 'area': 'JB Nagar / Marol Naka', 'lat': 19.1120, 'lng': 72.8720},
    '400093': {'city': 'Andheri', 'area': 'MIDC Central Road', 'lat': 19.1205, 'lng': 72.8755},
    '400058': {'city': 'Andheri', 'area': 'Andheri Station West', 'lat': 19.1197, 'lng': 72.8464},
    'andheri': {'city': 'Andheri', 'area': 'Central Andheri', 'lat': 19.1136, 'lng': 72.8697},

    # 9. Borivali
    '400092': {'city': 'Borivali', 'area': 'Shimpoli / SV Road / Borivali West', 'lat': 19.2275, 'lng': 72.8465},
    '400103': {'city': 'Borivali', 'area': 'IC Colony / Holy Cross', 'lat': 19.2450, 'lng': 72.8480},
    '400066': {'city': 'Borivali', 'area': 'Carter Road / National Park / Borivali East', 'lat': 19.2285, 'lng': 72.8630},
    '400091': {'city': 'Borivali', 'area': 'Borivali West Station', 'lat': 19.2290, 'lng': 72.8560},
    'borivali': {'city': 'Borivali', 'area': 'Central Borivali', 'lat': 19.2307, 'lng': 72.8567},

    # 10. Navi Mumbai
    '400703': {'city': 'Navi Mumbai', 'area': 'Sector 17 / Vashi', 'lat': 19.0760, 'lng': 72.9985},
    '400706': {'city': 'Navi Mumbai', 'area': 'Seawoods Grand Central / Nerul', 'lat': 19.0205, 'lng': 73.0185},
    '400705': {'city': 'Navi Mumbai', 'area': 'Palm Beach Road / Vashi', 'lat': 19.0680, 'lng': 73.0070},
    '400614': {'city': 'Navi Mumbai', 'area': 'CBD Belapur', 'lat': 19.0190, 'lng': 73.0395},
    '410210': {'city': 'Navi Mumbai', 'area': 'Sector 20 / Kharghar', 'lat': 19.0430, 'lng': 73.0670},
    'navi mumbai': {'city': 'Navi Mumbai', 'area': 'Central Navi Mumbai', 'lat': 19.0330, 'lng': 73.0297},
    'vashi': {'city': 'Navi Mumbai', 'area': 'Sector 17, Vashi', 'lat': 19.0760, 'lng': 72.9985},
    'nerul': {'city': 'Navi Mumbai', 'area': 'Nerul West', 'lat': 19.0335, 'lng': 73.0160},
    'kharghar': {'city': 'Navi Mumbai', 'area': 'Kharghar Sector 20', 'lat': 19.0430, 'lng': 73.0670},
    'seawoods': {'city': 'Navi Mumbai', 'area': 'Seawoods Mall', 'lat': 19.0205, 'lng': 73.0185},

    # Other Mumbai Landmark hubs
    '400050': {'city': 'Mumbai', 'area': 'Bandra West', 'lat': 19.0596, 'lng': 72.8295},
    '400001': {'city': 'Mumbai', 'area': 'Fort / Colaba', 'lat': 18.9322, 'lng': 72.8354},
    'mumbai': {'city': 'Mumbai', 'area': 'City Center (BKC / Dadar)', 'lat': 19.0760, 'lng': 72.8777},

    # Bengaluru
    '560038': {'city': 'Bengaluru', 'area': 'Indiranagar', 'lat': 12.9784, 'lng': 77.6408},
    '560034': {'city': 'Bengaluru', 'area': 'Koramangala', 'lat': 12.9352, 'lng': 77.6245},
    '560066': {'city': 'Bengaluru', 'area': 'Whitefield', 'lat': 12.9698, 'lng': 77.7500},
    '560001': {'city': 'Bengaluru', 'area': 'MG Road', 'lat': 12.9756, 'lng': 77.6066},
    'bengaluru': {'city': 'Bengaluru', 'area': 'City Center', 'lat': 12.9716, 'lng': 77.5946},
    'bangalore': {'city': 'Bengaluru', 'area': 'City Center', 'lat': 12.9716, 'lng': 77.5946},

    # New Delhi
    '110001': {'city': 'New Delhi', 'area': 'Connaught Place', 'lat': 28.6304, 'lng': 77.2177},
    'delhi': {'city': 'New Delhi', 'area': 'Central Delhi', 'lat': 28.6139, 'lng': 77.2090},

    # Hyderabad & Pune
    '500081': {'city': 'Hyderabad', 'area': 'Hitec City', 'lat': 17.4474, 'lng': 78.3762},
    'hyderabad': {'city': 'Hyderabad', 'area': 'City Center', 'lat': 17.3850, 'lng': 78.4867},
    '411001': {'city': 'Pune', 'area': 'Pune Station', 'lat': 18.5289, 'lng': 73.8744},
    'pune': {'city': 'Pune', 'area': 'City Center', 'lat': 18.5204, 'lng': 73.8567},
}


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points in kilometers.
    """
    R = 6371.0  # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


def resolve_coordinates(location_input: str) -> Optional[Tuple[float, float, str]]:
    """
    Resolve coordinates from PIN code or city name string.
    Returns (latitude, longitude, resolved_name) or None.
    """
    if not location_input:
        return None

    cleaned = location_input.strip().lower()
    
    # Check exact PIN code or city key
    if cleaned in KNOWN_GEOCODING_DATABASE:
        data = KNOWN_GEOCODING_DATABASE[cleaned]
        return data['lat'], data['lng'], f"{data['area']}, {data['city']}"

    # Partial match
    for key, data in KNOWN_GEOCODING_DATABASE.items():
        if key in cleaned or cleaned in key:
            return data['lat'], data['lng'], f"{data['area']}, {data['city']}"

    # Default fallback to Bengaluru tech hub if unrecognized
    return None


def find_nearby_stores_with_inventory(
    product_id: Optional[str] = None,
    customer_lat: float = 12.9716,
    customer_lng: float = 77.5946,
    max_radius_km: float = 25.0,
    required_quantity: int = 1
) -> List[Dict[str, Any]]:
    """
    Queries active stores within coverage radius that have available inventory for the product.
    Ranks by straight-line distance, road delivery estimate, and availability.
    """
    stores = Store.objects.filter(operatingStatus='Open')
    results = []

    for store in stores:
        dist_km = haversine_distance_km(customer_lat, customer_lng, store.latitude, store.longitude)
        
        # Check service coverage radius
        effective_radius = max(store.serviceCoverageRadiusKm, max_radius_km)
        if dist_km > effective_radius:
            continue

        store_data = {
            'storeId': store.id,
            'storeName': store.name,
            'sellerName': store.seller,
            'address': store.address,
            'city': store.city,
            'pincode': store.pincode,
            'latitude': store.latitude,
            'longitude': store.longitude,
            'distanceKm': dist_km,
            'operatingStatus': store.operatingStatus,
            'fulfillmentCapability': store.fulfillmentCapability,
            'rating': store.rating,
            'phone': store.phone,
            'openingHours': store.openingHours,
            # Estimated delivery minutes based on road distance
            'estimatedMinutes': max(25, int(dist_km * 3.2) + 15),
            'deliveryFee': 0.0 if dist_km <= 3.0 else round(35.0 + max(0, dist_km - 3.0) * 8.0, 2),
        }

        # Check inventory for specific product if requested
        if product_id:
            inv = StoreInventory.objects.filter(
                store=store,
                product_id=product_id,
                isAvailable=True,
                availableQuantity__gte=required_quantity
            ).first()

            if not inv:
                # Store does not have required stock
                continue

            store_data['availableQuantity'] = inv.availableQuantity
            store_data['storePrice'] = inv.storePrice
            store_data['isAvailable'] = True
            store_data['productId'] = product_id
        else:
            # General store lookup without product constraint
            store_data['availableQuantity'] = StoreInventory.objects.filter(store=store, isAvailable=True).count()
            store_data['isAvailable'] = True

        results.append(store_data)

    # Sort results by distance ascending
    results.sort(key=lambda s: s['distanceKm'])
    return results


def get_mumbai_zones_summary() -> List[Dict[str, Any]]:
    """
    Returns aggregated status for all 10 Mumbai Metropolitan Region operating zones,
    including active store count, central geospatial coordinates, and key hubs.
    """
    summary = []
    all_open_stores = list(Store.objects.filter(operatingStatus='Open'))

    for zone_id, zone_data in MUMBAI_ZONES.items():
        z_lat = zone_data['lat']
        z_lng = zone_data['lng']
        
        # Count stores within 8km radius of zone center or matching city name
        zone_stores = [
            s for s in all_open_stores
            if (s.city.lower() == zone_data['name'].lower() or
                s.pincode in zone_data['pincodes'] or
                haversine_distance_km(z_lat, z_lng, s.latitude, s.longitude) <= 8.5)
        ]

        summary.append({
            'id': zone_id,
            'name': zone_data['name'],
            'lat': z_lat,
            'lng': z_lng,
            'description': zone_data['description'],
            'pincodes': zone_data['pincodes'],
            'activeStoresCount': len(zone_stores),
            'featuredStores': [
                {
                    'id': s.id,
                    'name': s.name,
                    'seller': s.seller,
                    'address': s.address,
                    'rating': s.rating,
                    'lat': s.latitude,
                    'lng': s.longitude,
                    'pincode': s.pincode,
                    'capability': s.fulfillmentCapability
                }
                for s in zone_stores[:3]
            ]
        })

    return summary
