# KFRONT

<p align="center"><img src="https://github.com/user-attachments/assets/f5fc9dc4-fb8f-47d8-84c8-dca074639826" width="50%" height="50%"/></p>

KFRONT es una aplicación de consola escrita en Python para automatizar la administración y carga de trabajo en un cluster de monoprocesadores x86 bajo sistema operativo GNU/Linux y entorno LAM/MPI. Esta utilidad toma los comandos básicos de LAM y los ejecuta automáticamente para ahorrar tiempo en la modificación de los parámetros del cluster y envío de trabajo para ejecución.

El lenguaje de programación soportado por KFRONT es C, es decir, el programa del usuario debe estar escrito en lenguaje C. Asimismo, la versión actual de KFRONT no soporta programas que hagan uso de archivos suplementarios al ejecutable, por lo que deben ser copiados manualmente a cada uno de los nodos donde se ejecutará el programa.

Este repositorio contiene el código fuente de la aplicación KFRONT, algunos programas de ejemplo, un archivo de configuración de ejemplo y el manual de instrucciones de la aplicación. Se incluye además en este documento una guía básica de uso de KFRONT para aquellos usuarios que ya estén familiarizados con LAM y deseen explorar la aplicación por su propia cuenta.

La aplicación fue desarrollada utilizando un cluster particular para trabajos sencillos de MPI y, en consecuencia, la aplicación podría no adaptarse completamente a las necesidades de otro cluster.

## Guía Rápida
### Menú principal
1. Configuración del cluster: permite modificar los parámetros del cluster (agregar, quitar, reordenar nodos)
2. Iniciar LAM: arma archivo de configuración ```lamhosts```, lo copia al nodo maestro e inicia el entorno LAM (invoca ```lamboot -v lamhosts```)
3. Terminar LAM: termina el entorno LAM (invoca ```lamhalt```)
4. Compilar: compila el codigo fuente suministrado por el usuario en el nodo maestro (requiere que LAM esté activo)
5. Copiar: copia el binario resultante de 4 a todos los nodos (requiere que LAM esté activo)
6. Ejecutar: realiza 5 e invoca ```mpirun``` en el nodo maestro (requiere LAM activo y que se hayan ejecutado 4 y 5)
7. Compilar y Ejecutar: realiza 4, 5, 6 automáticamente (requiere LAM activo)
8. Salir: termina LAM (si está activo) y devuelve el control al operador de la consola.

### Configuración del cluster
1. Reordenar nodos: toma un par de IDs de nodos e intercambia sus posiciones en la tabla de nodos del cluster
2. Agregar nodo: toma una IP/nombre de un nodo, establece la conexión y lo agrega al final de la tabla de nodos, invocando ```lamgrow``` si LAM está activo
3. Quitar nodo: toma un ID de nodo y lo quita de la tabla de nodos, reiniciando LAM o invocando ```lamshrink``` cuando corresponda
4. Cambiar estado de nodo: toma un ID de nodo y modifica el estado (activo/inactivo) en la tabla de nodos
5. Reasignar maestro: toma un ID de nodo y lo asigna como maestro, posicionándolo además en la posición inicial (```n0```) de la tabla de nodos
6. Terminar y salir: regresa al menú principal.

### Convención de colores:
- Blanco: texto normal
- Verde: mensajes del sistema
- Rojo: error del sistema (puede ser fatal o no)
- Amarillo: resultados de ejecución
- Cian/Magenta: comandos ejecutados en segundo plano
