# DEFINICIÓN DE UMBRALES Y REGLAS POR SECTOR
# Estos valores calibrarán el motor de señales y las alertas del Dashboard.

SECTOR_CONFIGS = {
    "servicios": {
        "description": "Agencias, consultorías, freelancers y servicios profesionales.",
        "thresholds": {
            "min_profit_margin": 30.0,  # Los servicios suelen tener mayor margen (menos costos físicos)
            "max_expense_ratio": 60.0,  # Gasto máximo como % de ingresos
            "cash_reserve_months": 3    # Meses de reserva recomendados
        }
    },
    "comercio_digital": {
        "description": "E-commerce, tiendas online, dropshipping y venta digital.",
        "thresholds": {
            "min_profit_margin": 15.0,  # Márgenes más apretados por logística/ads
            "max_expense_ratio": 75.0,  
            "cash_reserve_months": 2    # Rotación rápida
        }
    },
    "comercio_fisico": {
        "description": "Tiendas, restaurantes, locales y negocios tradicionales.",
        "thresholds": {
            "min_profit_margin": 20.0,  # Afectado por alquileres y servicios
            "max_expense_ratio": 70.0,
            "cash_reserve_months": 4    # Mayor riesgo por costos fijos altos
        }
    },
    "emprendimiento": {
        "description": "Startups, proyectos en fase inicial o etapa de idea.",
        "thresholds": {
            "min_profit_margin": 10.0,  # En fase de crecimiento se prioriza reinversión
            "max_expense_ratio": 90.0,  # Alto gasto por adquisición/desarrollo
            "cash_reserve_months": 6    # Alta incertidumbre, requiere más pista (runway)
        }
    }
}

BUSINESS_TYPES = {
    "freelance": "Profesional Independiente / Freelance",
    "pequeno": "Pequeño Negocio (1-10 empleados)",
    "mediano": "Mediana Empresa (11-50 empleados)",
    "startup": "Startup en crecimiento"
}

def get_sector_thresholds(sector_key: str):
    """Devuelve las reglas de un sector o las reglas por defecto si no existe."""
    default_rules = {
        "min_profit_margin": 20.0,
        "max_expense_ratio": 70.0,
        "cash_reserve_months": 3
    }
    
    if not sector_key or sector_key not in SECTOR_CONFIGS:
        return default_rules
        
    return SECTOR_CONFIGS[sector_key]["thresholds"]