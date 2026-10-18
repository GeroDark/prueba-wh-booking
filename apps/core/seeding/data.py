"""Demo content loaded by `manage.py seed_data`.

Texts, contacts and photos come from the WH Figma design where it provides them; the rest is
plausible demo data. Translated values are (Spanish, English) tuples. Image paths are relative
to `seed/images/` (see seed/images/CREDITS.md). Tax rates are illustrative.
"""

SITE_SETTINGS = {
    "contact_email": "sales@wynwoodhouse.com",
    "whatsapp_number": "+51 947 022 549",
    "whatsapp_message": (
        "Hola, me gustaría información sobre estadías largas con Wynwood House.",
        "Hi, I'd like information about long stays with Wynwood House.",
    ),
}

HOME_PAGE = {
    "hero_title": ("Experiencia de hogar, calidad de hotel", "Home experience, hotel quality"),
    "hero_subtitle": ("Lo mejor de ambos mundos", "Best of both worlds"),
    "hero_image": "home/hero.jpg",
    "destinations_title": ("Descubre nuestros destinos", "Discover our destinations"),
    "featured_title": ("Propiedades destacadas", "Featured properties"),
    "featured_text": (
        "Descubre nuestra selección exclusiva de propiedades y conoce tu destino preferido a tu "
        "manera. Encuentra tu estadía ideal y empieza a vivir una experiencia única.",
        "Discover our exclusive selection of properties and get to know your favorite destination "
        "your way. Find your ideal stay and start living a unique experience.",
    ),
}

COUNTRIES = [
    {
        "code": "co",
        "slug": "colombia",
        "name": ("Colombia", "Colombia"),
        "image": "destinations/colombia.jpg",
    },
    {
        "code": "mx",
        "slug": "mexico",
        "name": ("México", "Mexico"),
        "image": "destinations/mexico.jpg",
    },
    {"code": "pe", "slug": "peru", "name": ("Perú", "Peru"), "image": "destinations/peru.jpg"},
    {
        "code": "pa",
        "slug": "panama",
        "name": ("Panamá", "Panama"),
        "image": "destinations/panama.jpg",
    },
    {"code": "es", "slug": "spain", "name": ("España", "Spain"), "image": "destinations/spain.jpg"},
]

TAXES = [
    {"country": "co", "name": ("IVA", "VAT"), "rate": "19.00"},
    {"country": "mx", "name": ("IVA", "VAT"), "rate": "16.00"},
    {"country": "mx", "name": ("Impuesto de ciudad", "City tax"), "rate": "3.00"},
    {"country": "pe", "name": ("IGV", "VAT"), "rate": "18.00"},
    {"country": "pa", "name": ("ITBMS", "VAT"), "rate": "10.00"},
    {"country": "es", "name": ("IVA", "VAT"), "rate": "10.00"},
]

CITIES = [
    {
        "country": "co",
        "slug": "bogota",
        "name": ("Bogotá", "Bogota"),
        "timezone": "America/Bogota",
        "districts": [
            ("chico", "Chicó"),
            ("virrey", "Virrey"),
            ("chapinero", "Chapinero"),
            ("parque-93", "Parque 93"),
            ("cabrera", "Cabrera"),
        ],
    },
    {
        "country": "co",
        "slug": "cartagena",
        "name": ("Cartagena", "Cartagena"),
        "timezone": "America/Bogota",
        "districts": [("bocagrande", "Bocagrande"), ("getsemani", "Getsemaní")],
    },
    {
        "country": "mx",
        "slug": "ciudad-de-mexico",
        "name": ("Ciudad de México", "Mexico City"),
        "timezone": "America/Mexico_City",
        "districts": [("condesa", "Condesa"), ("roma-norte", "Roma Norte"), ("polanco", "Polanco")],
    },
    {
        "country": "pe",
        "slug": "lima",
        "name": ("Lima", "Lima"),
        "timezone": "America/Lima",
        "districts": [
            ("miraflores", "Miraflores"),
            ("barranco", "Barranco"),
            ("san-isidro", "San Isidro"),
        ],
    },
    {
        "country": "pa",
        "slug": "ciudad-de-panama",
        "name": ("Ciudad de Panamá", "Panama City"),
        "timezone": "America/Panama",
        "districts": [("casco-viejo", "Casco Viejo"), ("punta-pacifica", "Punta Pacífica")],
    },
    {
        "country": "es",
        "slug": "madrid",
        "name": ("Madrid", "Madrid"),
        "timezone": "Europe/Madrid",
        "districts": [("malasana", "Malasaña"), ("salamanca", "Salamanca")],
    },
    {
        "country": "es",
        "slug": "barcelona",
        "name": ("Barcelona", "Barcelona"),
        "timezone": "Europe/Madrid",
        "districts": [("gracia", "Gràcia"), ("eixample", "Eixample")],
    },
]

AMENITIES = [
    {"icon": "wifi", "name": ("Wi-Fi", "Wi-Fi")},
    {"icon": "tv", "name": ("Smart TV", "Smart TV")},
    {"icon": "snow", "name": ("Aire acondicionado", "Air conditioning")},
    {"icon": "fork-knife", "name": ("Cocina equipada", "Equipped kitchen")},
    {"icon": "laptop", "name": ("Zona de trabajo", "Workspace")},
    {"icon": "p-square", "name": ("Estacionamiento", "Parking")},
    {"icon": "arrow-down-up", "name": ("Ascensor", "Elevator")},
    {"icon": "shield-check", "name": ("Portería 24/7", "24/7 doorman")},
    {"icon": "tree", "name": ("Balcón o terraza", "Balcony or terrace")},
    {"icon": "water", "name": ("Piscina", "Pool")},
    {"icon": "fire", "name": ("Parrilla", "BBQ grill")},
    {"icon": "heart-pulse", "name": ("Gimnasio", "Gym")},
    {"icon": "key", "name": ("Check-in sin contacto", "Contactless check-in")},
]

BASIC = ["wifi", "tv", "fork-knife", "key"]

PROPERTIES = [
    {
        "slug": "modern-duplex-parque-virrey",
        "title": ("Dúplex moderno en Parque Virrey", "Modern duplex in Parque Virrey"),
        "description": (
            "Dúplex luminoso a pasos del Parque El Virrey, con sala a doble altura, cocina abierta "
            "y una habitación en el segundo nivel. Ideal para parejas que buscan caminar a "
            "restaurantes, cafés y zonas verdes del norte de Bogotá.",
            "Bright duplex steps away from El Virrey Park, with a double-height living room, open "
            "kitchen and a bedroom upstairs. Ideal for couples who want to walk to restaurants, "
            "cafés and green areas in northern Bogotá.",
        ),
        "city": "bogota",
        "district": "virrey",
        "address": "Calle 88 # 15-23",
        "coordinates": ("4.673100", "-74.053300"),
        "guests": 2,
        "bedrooms": 1,
        "beds": 1,
        "bathrooms": 1,
        "price": "83.00",
        "cleaning": "20.00",
        "featured": True,
        "amenities": [*BASIC, "laptop", "arrow-down-up", "shield-check"],
        "images": [
            "properties/duplex-living.jpg",
            "properties/duplex-bedroom.jpg",
            "properties/duplex-kitchen.jpg",
        ],
    },
    {
        "slug": "natural-1br-private-terrace-cartagena",
        "title": (
            "Natural 1BR con terraza privada en Cartagena",
            "Natural 1BR with private terrace in Cartagena",
        ),
        "description": (
            "Apartamento de una habitación con terraza privada y acceso a piscina, en un edificio "
            "rodeado de vegetación. A pocos minutos de la playa de Bocagrande y de la Ciudad Amurallada.",
            "One-bedroom apartment with a private terrace and pool access, in a building surrounded "
            "by greenery. A few minutes from Bocagrande beach and the Walled City.",
        ),
        "city": "cartagena",
        "district": "bocagrande",
        "address": "Carrera 1 # 9-120",
        "coordinates": ("10.399700", "-75.555900"),
        "guests": 3,
        "bedrooms": 1,
        "beds": 2,
        "bathrooms": 1,
        "price": "145.00",
        "cleaning": "35.00",
        "featured": True,
        "amenities": [*BASIC, "snow", "water", "tree", "shield-check"],
        "images": ["properties/featured-3.jpg", "properties/featured-4.jpg"],
    },
    {
        "slug": "cozy-loft-luxury-building-chico",
        "title": (
            "Loft acogedor en edificio de lujo en Chicó",
            "Cozy loft in a luxury building in Chicó",
        ),
        "description": (
            "Loft con ventanales de piso a techo, zona de trabajo y acceso a gimnasio. Ubicado en "
            "uno de los barrios más tranquilos y seguros de Bogotá.",
            "Loft with floor-to-ceiling windows, a workspace and gym access. Located in one of the "
            "quietest and safest neighborhoods in Bogotá.",
        ),
        "city": "bogota",
        "district": "chico",
        "address": "Carrera 11 # 94-46",
        "coordinates": ("4.678200", "-74.048900"),
        "guests": 2,
        "bedrooms": 1,
        "beds": 1,
        "bathrooms": 1,
        "price": "120.00",
        "cleaning": "25.00",
        "featured": False,
        "amenities": [*BASIC, "laptop", "heart-pulse", "arrow-down-up", "p-square"],
        "images": ["properties/results-2.jpg", "properties/results-1.jpg"],
    },
    {
        "slug": "dazzling-2br-condesa",
        "title": ("Deslumbrante 2BR en Condesa", "Dazzling 2BR in Condesa"),
        "description": (
            "Departamento de dos habitaciones con sala amplia y mucha luz natural, en el corazón de "
            "la Condesa. Rodeado de parques, cafeterías y galerías.",
            "Two-bedroom apartment with a spacious living room and plenty of natural light, in the "
            "heart of Condesa. Surrounded by parks, cafés and galleries.",
        ),
        "city": "ciudad-de-mexico",
        "district": "condesa",
        "address": "Av. Ámsterdam 210",
        "coordinates": ("19.411800", "-99.170200"),
        "guests": 4,
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 2,
        "price": "135.00",
        "cleaning": "40.00",
        "featured": True,
        "amenities": [*BASIC, "laptop", "tree", "arrow-down-up"],
        "images": ["properties/featured-1.jpg", "properties/results-1.jpg"],
    },
    {
        "slug": "awesome-2br-panoramic-view-miraflores",
        "title": (
            "Increíble 2BR con vista panorámica en Miraflores",
            "Awesome 2BR with panoramic view in Miraflores",
        ),
        "description": (
            "Departamento con vista al océano Pacífico, sala con ventanales y dos habitaciones. "
            "A pocas cuadras del Malecón de Miraflores y del Parque Kennedy.",
            "Apartment overlooking the Pacific Ocean, with a living room with large windows and two "
            "bedrooms. A few blocks from the Miraflores boardwalk and Kennedy Park.",
        ),
        "city": "lima",
        "district": "miraflores",
        "address": "Calle Alcanfores 1262, Miraflores 15074",
        "coordinates": ("-12.124500", "-77.029100"),
        "guests": 4,
        "bedrooms": 2,
        "beds": 3,
        "bathrooms": 2,
        "price": "110.00",
        "cleaning": "30.00",
        "featured": True,
        "amenities": [*BASIC, "snow", "arrow-down-up", "shield-check", "laptop"],
        "images": ["properties/miraflores-living.jpg", "properties/results-4.jpg"],
    },
    {
        "slug": "bohemian-studio-barranco",
        "title": ("Estudio bohemio en Barranco", "Bohemian studio in Barranco"),
        "description": (
            "Estudio de diseño cerca del Puente de los Suspiros, perfecto para una escapada "
            "creativa entre galerías, bares y miradores al mar.",
            "Design studio near the Bridge of Sighs, perfect for a creative getaway among "
            "galleries, bars and ocean viewpoints.",
        ),
        "city": "lima",
        "district": "barranco",
        "address": "Jr. Batallón Ayacucho 271",
        "coordinates": ("-12.149500", "-77.022100"),
        "guests": 2,
        "bedrooms": 1,
        "beds": 1,
        "bathrooms": 1,
        "price": "70.00",
        "cleaning": "15.00",
        "featured": False,
        "amenities": [*BASIC, "laptop"],
        "images": ["properties/results-3.jpg", "properties/duplex-bedroom.jpg"],
    },
    {
        "slug": "executive-apartment-parque-93",
        "title": ("Apartamento ejecutivo en Parque 93", "Executive apartment in Parque 93"),
        "description": (
            "Espacio cálido con acabados en madera, cocina integrada y una habitación. Pensado para "
            "viajes de trabajo, a pasos de oficinas y restaurantes del Parque 93.",
            "Warm space with wooden finishes, an open kitchen and one bedroom. Designed for "
            "business trips, steps away from Parque 93 offices and restaurants.",
        ),
        "city": "bogota",
        "district": "parque-93",
        "address": "Calle 93B # 13-44",
        "coordinates": ("4.676800", "-74.048200"),
        "guests": 3,
        "bedrooms": 1,
        "beds": 2,
        "bathrooms": 1,
        "price": "95.00",
        "cleaning": "20.00",
        "featured": False,
        "amenities": [*BASIC, "laptop", "p-square", "shield-check"],
        "images": ["properties/featured-2.jpg", "properties/duplex-kitchen.jpg"],
    },
    {
        "slug": "garden-flat-roma-norte",
        "title": ("Departamento con jardín en Roma Norte", "Garden flat in Roma Norte"),
        "description": (
            "Planta baja con jardín interior en una casona restaurada de la colonia Roma. Calles "
            "arboladas, mercados y la mejor escena gastronómica de la ciudad.",
            "Ground-floor flat with an inner garden in a restored mansion in Roma. Tree-lined "
            "streets, markets and the city's best food scene.",
        ),
        "city": "ciudad-de-mexico",
        "district": "roma-norte",
        "address": "Calle Colima 158",
        "coordinates": ("19.418700", "-99.160300"),
        "guests": 2,
        "bedrooms": 1,
        "beds": 1,
        "bathrooms": 1,
        "price": "90.00",
        "cleaning": "25.00",
        "featured": False,
        "amenities": [*BASIC, "tree", "laptop"],
        "images": ["properties/results-1.jpg", "properties/results-3.jpg"],
    },
    {
        "slug": "colonial-suite-casco-viejo",
        "title": ("Suite colonial en Casco Viejo", "Colonial suite in Casco Viejo"),
        "description": (
            "Suite con piscina compartida en el Casco Viejo, Patrimonio de la Humanidad. Ideal para "
            "recorrer a pie plazas, iglesias y rooftops con vista a la bahía.",
            "Suite with a shared pool in Casco Viejo, a UNESCO World Heritage Site. Ideal for "
            "walking to squares, churches and rooftops overlooking the bay.",
        ),
        "city": "ciudad-de-panama",
        "district": "casco-viejo",
        "address": "Calle 8 Este, San Felipe",
        "coordinates": ("8.952600", "-79.535300"),
        "guests": 2,
        "bedrooms": 1,
        "beds": 1,
        "bathrooms": 1,
        "price": "115.00",
        "cleaning": "30.00",
        "featured": False,
        "amenities": [*BASIC, "snow", "water"],
        "images": ["properties/featured-4.jpg", "properties/featured-3.jpg"],
    },
    {
        "slug": "designer-apartment-malasana",
        "title": ("Apartamento de diseño en Malasaña", "Designer apartment in Malasaña"),
        "description": (
            "Apartamento reformado con techos altos y balcón a una calle peatonal de Malasaña. "
            "A diez minutos a pie de la Gran Vía y del centro histórico de Madrid.",
            "Renovated apartment with high ceilings and a balcony over a pedestrian street in "
            "Malasaña. A ten-minute walk from Gran Vía and Madrid's historic center.",
        ),
        "city": "madrid",
        "district": "malasana",
        "address": "Calle del Espíritu Santo 18",
        "coordinates": ("40.424700", "-3.703300"),
        "guests": 3,
        "bedrooms": 1,
        "beds": 2,
        "bathrooms": 1,
        "price": "125.00",
        "cleaning": "35.00",
        "featured": True,
        "amenities": [*BASIC, "snow", "tree", "arrow-down-up"],
        "images": ["properties/results-4.jpg", "properties/featured-1.jpg"],
    },
    {
        "slug": "classic-flat-salamanca",
        "title": (
            "Piso clásico en el barrio de Salamanca",
            "Classic flat in the Salamanca district",
        ),
        "description": (
            "Piso señorial de dos habitaciones junto al Parque del Retiro y a las boutiques de la "
            "calle Serrano. Elegancia clásica con todas las comodidades actuales.",
            "Stately two-bedroom flat next to Retiro Park and the boutiques of Calle Serrano. "
            "Classic elegance with every modern comfort.",
        ),
        "city": "madrid",
        "district": "salamanca",
        "address": "Calle de Velázquez 45",
        "coordinates": ("40.427900", "-3.683700"),
        "guests": 4,
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 2,
        "price": "160.00",
        "cleaning": "40.00",
        "featured": False,
        "amenities": [*BASIC, "snow", "arrow-down-up", "shield-check", "laptop"],
        "images": ["properties/duplex-bedroom.jpg", "properties/featured-2.jpg"],
    },
    {
        "slug": "light-filled-loft-gracia",
        "title": ("Loft luminoso en Gràcia", "Light-filled loft in Gràcia"),
        "description": (
            "Loft abierto con cocina equipada en el barrio de Gràcia, entre plazas con terrazas y a "
            "un paseo de la Casa Batlló y el Park Güell.",
            "Open-plan loft with an equipped kitchen in Gràcia, among squares with terraces and a "
            "short walk from Casa Batlló and Park Güell.",
        ),
        "city": "barcelona",
        "district": "gracia",
        "address": "Carrer de Verdi 32",
        "coordinates": ("41.404000", "2.157800"),
        "guests": 2,
        "bedrooms": 1,
        "beds": 1,
        "bathrooms": 1,
        "price": "105.00",
        "cleaning": "30.00",
        "featured": True,
        "amenities": [*BASIC, "snow", "laptop"],
        "images": ["properties/duplex-kitchen.jpg", "properties/duplex-living.jpg"],
    },
]

FEATURE_SECTIONS = [
    {
        "key": "services",
        "title": ("Servicios en Wynwood House", "Services at Wynwood House"),
        "text": (
            "Descubre los servicios que ofrecen nuestras propiedades para hacer de tu estadía la "
            "experiencia más cómoda y emocionante que puedas imaginar.",
            "Discover the services our properties offer to make your stay the most comfortable and "
            "exciting experience you can imagine.",
        ),
        "items": [
            {
                "title": ("Check-in sin contacto", "Contactless check-in"),
                "image": "services/contactless-check-in.jpg",
            },
            {
                "title": ("Limpieza profesional", "Professional cleaning"),
                "image": "services/professional-cleaning.jpg",
            },
            {"title": ("Wi-Fi", "Wi-Fi"), "image": "services/wifi.jpg"},
            {"title": ("Kit de baño", "Bath kit"), "image": "services/bath-kit.jpg"},
            {
                "title": ("Cocina equipada", "Equipped kitchen"),
                "image": "services/equipped-kitchen.jpg",
            },
            {"title": ("Pet friendly", "Pet friendly"), "image": "services/pet-friendly.jpg"},
            {"title": ("Soporte 24/7", "24/7 support"), "image": "services/support-24-7.jpg"},
            {"title": ("Cama Wynwood", "Wynwood bed"), "image": "services/wynwood-bed.jpg"},
        ],
    },
    {
        "key": "why-spain",
        "title": ("¿Por qué viajar a España?", "Why travel to Spain?"),
        "text": (
            "España combina siglos de historia, una de las gastronomías más reconocidas del mundo y "
            "costas para todos los gustos. Estas son algunas razones para elegirla como tu próximo "
            "destino.",
            "Spain combines centuries of history, one of the world's most celebrated cuisines and "
            "coastlines for every taste. Here are a few reasons to make it your next destination.",
        ),
        "items": [
            {
                "title": ("Gastronomía", "Food"),
                "description": (
                    "De las tapas a la paella: cocina de mercado, vinos con denominación de origen "
                    "y restaurantes de referencia mundial.",
                    "From tapas to paella: market cuisine, designation-of-origin wines and "
                    "world-renowned restaurants.",
                ),
                "image": "spain/gastronomy.jpg",
            },
            {
                "title": ("Cultura e historia", "Culture and history"),
                "description": (
                    "La Alhambra, el Museo del Prado y la Mezquita de Córdoba: siglos de historia "
                    "en cada ciudad.",
                    "The Alhambra, the Prado Museum and the Mosque of Córdoba: centuries of history "
                    "in every city.",
                ),
                "image": "spain/culture.jpg",
            },
            {
                "title": ("Playas y costa", "Beaches and coast"),
                "description": (
                    "Mediterráneo y Atlántico: desde calas escondidas hasta playas urbanas como "
                    "La Concha, en San Sebastián.",
                    "Mediterranean and Atlantic: from hidden coves to city beaches like La Concha "
                    "in San Sebastián.",
                ),
                "image": "spain/beaches.jpg",
            },
            {
                "title": ("Arquitectura", "Architecture"),
                "description": (
                    "De la Sagrada Familia de Gaudí al Madrid de los Austrias: ciudades para "
                    "recorrer a pie.",
                    "From Gaudí's Sagrada Familia to Habsburg Madrid: cities made for walking.",
                ),
                "image": "spain/architecture.jpg",
            },
        ],
    },
]

BANNERS = [
    {
        "key": "long-stay",
        "title": ("Alquileres a largo plazo", "Long-term rentals"),
        "text": (
            "Descubre el confort y la conveniencia de hospedarte con nosotros durante períodos "
            "prolongados. Aprovecha nuestras tarifas especiales diseñadas exclusivamente para "
            "estadías largas, ofreciéndote una experiencia continua de calidad y comodidad.",
            "Discover the comfort and convenience of staying with us for extended periods. Take "
            "advantage of our special rates designed exclusively for long stays, offering you a "
            "continuous experience of quality and comfort.",
        ),
        "image": "banners/long-stay.jpg",
        "layout": "image_left",
        "cta_label": ("Contáctanos", "Contact us"),
        "cta_target": "whatsapp",
        "cta_url": "",
        "order": 2,
    },
    {
        "key": "events",
        "title": ("¡Disfruta de nuestros eventos!", "Enjoy our events!"),
        "text": (
            "Vive tu experiencia al máximo mientras te sumerges en el vibrante mundo de los eventos "
            "Wynwood. Disfruta de arte, cultura e inspiración como nunca antes.",
            "Make the most of your experience as you dive into the vibrant world of Wynwood "
            "events. Enjoy art, culture and inspiration like never before.",
        ),
        "image": "banners/events-2.jpg",
        "layout": "image_right",
        "cta_label": ("Ver todos los eventos", "See all events"),
        "cta_target": "link",
        "cta_url": "https://wynwoodhouse.com/",
        "order": 1,
    },
    {
        "key": "real-estate",
        "title": ("Invierte en real estate", "Invest in real estate"),
        "text": (
            "Compra o vende tu propiedad y obtén asesoramiento profesional y una experiencia sin estrés.",
            "Buy or sell your property and get professional advice and a stress-free experience.",
        ),
        "image": "banners/real-estate.jpg",
        "layout": "background",
        "cta_label": ("Saber más", "Learn more"),
        "cta_target": "link",
        "cta_url": "https://wynwoodhouse.com/",
        "order": 3,
    },
]

WH_SITE = "https://wynwoodhouse.com/"

MENUS = [
    {
        "placement": "header",
        "title": ("", ""),
        "links": [
            ("Casa Wynwood", "Casa Wynwood"),
            ("The Collection*", "The Collection*"),
            ("Publica tu propiedad", "List your property"),
            ("Invierte en bienes raíces", "Invest in real estate"),
        ],
    },
    {
        "placement": "footer",
        "title": ("Servicios", "Services"),
        "links": [
            ("Grupos y largas estadías", "Groups and long stays"),
            ("Eventos y producciones", "Events and productions"),
        ],
    },
    {
        "placement": "footer",
        "title": ("Nosotros", "About us"),
        "links": [
            ("¿Quiénes somos?", "Who we are"),
            ("Blog y noticias", "Blog and news"),
            ("Casa Wynwood", "Casa Wynwood"),
            ("Trabaja con nosotros", "Work with us"),
        ],
    },
    {
        "placement": "footer",
        "title": ("Propietarios e inversionistas", "Owners and investors"),
        "links": [("Wynwood Real Estate", "Wynwood Real Estate"), ("Propietarios", "Owners")],
    },
    {
        "placement": "footer",
        "title": ("Beneficios", "Benefits"),
        "links": [("Guías", "Guides"), ("Programa de recompensas", "Rewards program")],
    },
    {
        "placement": "footer",
        "title": ("Términos y condiciones", "Terms and conditions"),
        "links": [
            ("Términos de servicio", "Terms of service"),
            ("Política de privacidad", "Privacy policy"),
            ("Política de cancelación", "Cancellation policy"),
        ],
    },
]

CONTACT_CHANNELS = [
    {
        "kind": "whatsapp",
        "value": "+51 947 022 549",
        "country_code": "pe",
        "label": ("Perú", "Peru"),
    },
    {
        "kind": "whatsapp",
        "value": "+57 323 811 0133",
        "country_code": "co",
        "label": ("Colombia", "Colombia"),
    },
    {
        "kind": "whatsapp",
        "value": "+52 55 1693 9489",
        "country_code": "mx",
        "label": ("México", "Mexico"),
    },
    {
        "kind": "phone",
        "value": "+1 (253) 642-3881",
        "country_code": "us",
        "label": ("Estados Unidos", "United States"),
    },
    {
        "kind": "email",
        "value": "sales@wynwoodhouse.com",
        "country_code": "",
        "label": ("Ventas", "Sales"),
    },
]

SOCIAL_LINKS = [
    {"network": "facebook", "url": "https://www.facebook.com/wynwoodhouse"},
    {"network": "instagram", "url": "https://www.instagram.com/wynwood.house/"},
    {"network": "linkedin", "url": "https://www.linkedin.com/company/wynwood-house/"},
]

DEMO_USER = {
    "email": "demo@wynwoodhouse.test",
    "full_name": "Huésped Demo",
    "password": "Wynwood-Demo-2026",
}
