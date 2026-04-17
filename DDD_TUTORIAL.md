# Tutorial Avanzado de Domain-Driven Design (DDD)

Este tutorial te guiará desde los conceptos fundamentales hasta patrones avanzados para resolver problemas de software complejos.

## 1. Conceptos Fundamentales

### El Corazón del DDD: El Dominio
El **Dominio** es el problema que tu software intenta resolver. El objetivo de DDD es que la estructura del código sea un espejo del modelo mental de los expertos en el negocio.

### Lenguaje Ubicuo (Ubancuous Language)
Es el lenguaje común compartido entre desarrolladores y expertos de negocio. Si el experto dice "Pedido", el código debe tener una clase `Pedido`, no `OrderRequest` o `PurchaseRecord`. Evita la "traducción" constante que genera errores.

### Contextos Delimitados (Bounded Contexts)
En sistemas grandes, un mismo término puede significar cosas distintas. Por ejemplo, "Producto" en el contexto de **Ventas** tiene precio y descripción; en el contexto de **Logística**, tiene peso y dimensiones. DDD propone dividir el sistema en contextos separados y claros para evitar modelos gigantes e inmanejables.

---

## 2. Los Bloques de Construcción (Patrones de Diseño)

### Entidades (Entities)
Objetos que tienen una identidad única que persiste en el tiempo, independientemente de sus atributos.
*Ejemplo: Un `Usuario` es el mismo aunque cambie su email.*

### Objetos de Valor (Value Objects)
Objetos que se definen únicamente por sus atributos. No tienen identidad propia; si dos son iguales en valor, son el mismo objeto. Son **inmutables** por definición para evitar efectos secundarios.
*Ejemplo: Una `Direccion` o un `Dinero` (si el monto y la moneda son iguales, son idénticos).*

### Agregados (Aggregates)
Un grupo de entidades y objetos de valor que se tratan como una sola unidad para cambios de datos. Cada agregado tiene un **Aggregate Root** (Raíz del Agregado), que es el único punto de entrada para modificar el contenido del agregado. El Agregado garantiza la consistencia de sus reglas internas (**Invariantes**).

### Repositorios (Repositories)
Interfaces que actúan como una colección de objetos en memoria, permitiendo recuperar y guardar Agregados de forma persistente, ocultando la complejidad de la base de datos o servicios externos.

---

## 3. Conceptos Avanzados para Sistemas Complejos

### Context Mapping (Mapeo de Contextos)
Es la técnica para definir cómo interactúan los diferentes *Bounded Contexts*. Algunos patrones comunes son:
*   **Shared Kernel:** Dos contextos comparten un pequeño trozo de modelo (código).
*   **Customer-Supplier:** Un contexto depende de la evolución de otro.
*   **Conformist:** Un equipo acepta el modelo de otro sin intentar cambiarlo.
*   **Anti-Corruption Layer (ACL):** Una capa que traduce el modelo de un sistema externo "sucio" al modelo limpio de tu dominio, evitando que la contaminación externa entre en tu contexto.

### Domain Events (Eventos de Dominio)
Un evento es algo que **ya sucedió** en el dominio y que otros contextos o agregados pueden querer saber.
*Ejemplo: `PedidoPagado`, `StockAgotado`. Permiten el desacoplamiento total mediante comunicación asíncrona.*

### Domain Services vs Application Services
Es crucial no confundirlos:
*   **Domain Service:** Contiene lógica de negocio que no pertenece naturalmente a una sola Entidad o Agregado (ej. un cálculo complejo de impuestos que involucra múltiples reglas). Vive en la capa de **Dominio**.
*   **Application Service:** Orquesta la ejecución de casos de uso. Busca el agregado, llama al servicio de dominio y guarda el resultado. No tiene "lógica" de negocio, solo "flujo". Vive en la capa de **Aplicación**.

---

## 4. Capas de Arquitectura (Arquitectura Hexagonal / Onion)

Para implementar DDD con éxito, se utiliza una arquitectura orientada a capas o al centro:

1.  **Capa de Dominio (El Núcleo):** Contiene la lógica de negocio pura (Entidades, Value Objects, Reglas, Interfaces de Repositorio). No tiene dependencias externas.
2.  **Capa de Aplicación:** Coordina las tareas y define los Casos de Uso. Utiliza interfaces del dominio para interactuar con el mundo exterior sin conocer su implementación.
3.  **Capa de Infraestructura (La Periferia):** Implementaciones técnicas (Base de datos, envío de emails, llamadas a APIs externas, adaptadores de mensajería).
4.  **Capa de Interfaz/API:** La puerta de entrada al sistema (REST, GraphQL, CLI, UI).

---

## 5. Ejercicio Práctico: Sistema de Pedidos Avanzado

### Paso 1: Definir el Lenguaje Ubicuo y Eventos
*   **Pedido**: Agregado principal.
*   **Evento `PedidoConfirmado`**: Se dispara cuando el pago es exitoso.

### Paso 2: Implementación (Python)

```python
# --- Capa de Dominio ---
class Dinero: # Value Object Inmutable
    def __init__(self, cantidad: float, moneda: str):
        self._cantidad = cantidad
        self._moneda = moneda
    
    @property
    def cantidad(self): return self._cantidad

class Pedido: # Aggregate Root
    def __init__(self, id: str, cliente_id: str):
        self.id = id
        self.cliente_id = cliente_id
        self.items = []
        self.total = Dinero(0, "USD")
        self.eventos = [] # Lista de eventos para disparar luego

    def agregar_item(self, producto_id: str, precio: Dinero):
        # Validación de Invariante (Regla de negocio)
        if precio.cantidad <= 0:
            raise ValueError("El precio debe ser positivo")
        
        self.items.append({'id': producto_id, 'precio': precio})
        self.total = Dinero(self.total.cantidad + precio.cantidad, "USD")

    def confirmar_pago(self):
        # Lógica de negocio: Al confirmar, generamos un evento
        self.eventos.append("PedidoConfirmado")

# --- Capa de Aplicación ---
class PedidoService:
    def __init__(self, pedido_repo, event_bus):
        self.repo = pedido_repo
        self.bus = event_bus

    def procesar_pago(self, pedido_id: str):
        # 1. Orquestación
        pedido = self.repo.buscar(pedido_id)
        
        # 2. Ejecución de lógica de dominio
        pedido.confirmar_pago()
        
        # 3. Persistencia
        self.repo.guardar(pedido)
        
        # 4. Difusión de eventos (Side effects)
        for evento in pedido.eventos:
            self.bus.publicar(evento)

# --- Capapa de Infraestructura ---
class SqlPedidoRepository: # Implementación real
    def buscar(self, id): ... 
    def guardar(self, pedido): ...
```

## 6. Resumen de Buenas Prácticas
1.  **Mantén el Dominio puro:** No metas SQL ni librerías de frameworks en tus Entidades.
2.  **Protege las Invariantes:** El Agregado debe asegurar que sus reglas nunca se rompan. Si un dato es inválido, la entidad no debe permitir el cambio.
3.  **Usa Interfaces para la Infraestructura:** Define el Repositorio como una interfaz en el Dominio, e impleméntalo en la capa de Infraestructura (Inversión de Dependencia).
4.  **Evita Anemia del Modelo:** No crees "Entidades" que sean solo bolsas de datos (getters y setters). La lógica debe estar dentro de los objetos de dominio.
