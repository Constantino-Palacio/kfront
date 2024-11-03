# KFRONT

<p align="center"><img src="https://github.com/user-attachments/assets/f5fc9dc4-fb8f-47d8-84c8-dca074639826" width="50%" height="50%"/></p>

KFRONT es una aplicación de consola escrita en Python para automatizar la administración y carga de trabajo en un cluster de monoprocesadores x86 bajo sistema operativo GNU/Linux y entorno LAM/MPI. Esta utilidad toma los comandos básicos de LAM y los ejecuta automáticamente para ahorrar tiempo en la modificación de los parámetros del cluster y envío de trabajo para ejecución.

El lenguaje de programación soportado por KFRONT es C, es decir, el programa del usuario debe estar escrito en lenguaje C. Asimismo, la versión actual de KFRONT no soporta programas que hagan uso de archivos suplementarios al ejecutable, por lo que deben ser copiados manualmente a cada uno de los nodos donde se ejecutará el programa.

Este repositorio contiene el código fuente de la aplicación KFRONT, algunos programas de ejemplo, un archivo de configuración de ejemplo y el manual de instrucciones de la aplicación. Se incluye además en este documento una guía básica de uso de KFRONT para aquellos usuarios que ya estén familiarizados con LAM y deseen explorar la aplicación por su propia cuenta.

La aplicación fue desarrollada utilizando un cluster particular para trabajos sencillos de MPI y, en consecuencia, la aplicación podría no adaptarse completamente a las necesidades de otro cluster.
