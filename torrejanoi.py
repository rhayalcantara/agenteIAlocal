def hanoi(n, origen, destino, auxiliar, pasos):
    """Resuelve la Torre de Hanoi y guarda los pasos."""
    if n == 1:
        pasos.append(f"Mover disco 1 de {origen} a {destino}")
        return
    hanoi(n - 1, origen, auxiliar, destino, pasos)
    pasos.append(f"Mover disco {n} de {origen} a {destino}")
    hanoi(n - 1, auxiliar, destino, origen, pasos)

def resolver_torre_hanoi(num_discos, num_postes):
    """Resuelve la Torre de Hanoi con validaciones."""
    if num_discos < 3 or num_discos > 5:
        return "Error: El número de discos debe estar entre 3 y 5."
    if num_postes < 3 or num_postes > 5:
        return "Error: El número de postes debe estar entre 3 y 5."
    
    # Nombres de los postes (A, B, C, D, E)
    postes = [f"Poste {i+1}" for i in range(num_postes)]
    origen = postes[0]
    destino = postes[-1]
    auxiliar = postes[1:-1]  # Postes auxiliares

    pasos = []
    hanoi(num_discos, origen, destino, auxiliar[0] if auxiliar else "", pasos)

    return "\n".join(pasos)

import sys

# Ejemplo de uso
if __name__ == "__main__":
    try:
        if len(sys.argv) == 3:
            num_discos = int(sys.argv[1])
            num_postes = int(sys.argv[2])
        else:
            num_discos = int(input("Ingresa el número de discos (3-5): "))
            num_postes = int(input("Ingresa el número de postes (3-5): "))
            
        resultado = resolver_torre_hanoi(num_discos, num_postes)
        print("\nPasos para resolver la Torre de Hanoi:\n")
        print(resultado)
        print(f"\nTotal de iteraciones (pasos): {len(resultado.splitlines()) if 'Error' not in resultado else 0}")
    except ValueError:
        print("Por favor, ingresa números enteros válidos.")