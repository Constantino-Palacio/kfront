#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#--------------------------------------------------------------------------------------------------------------
# KFRONT -- Una herramienta para gestionar la carga de trabajo en un cluster basado en LAM/MPI. Admite la
# carga y ejecucion de programas escritos en lenguaje C y automatiza la administracion y configuracion de los
# parametros de un cluster de monoprocesadores.
#
# Uso: se invoca con o sin argumentos. El unico argumento que se procesa es una ruta de acceso a un archivo de
# texto plano que contiene una lista de nombres/direcciones IP de los distintos nodos del clustes. De no
# recibirse ningun argumento, se arma una lista por defecto con los nodos "alfa00" a "alfa04" (direcciones IP
# en rango 192.168.1.200 a 192.168.1.204.
#
# Version: OCT/24
#
# Autor: Constantino A. Palacio.
#--------------------------------------------------------------------------------------------------------------

import os
import subprocess
import sys
import tempfile
import time

# Obtener el directorio home del usuario
home_dir = os.environ['HOME']

maestro = "-"

nodos = []

#
# variables para almacenar los directorios de los archivos fuente y binario
#
ruta_fuente = "-"
nombre_fuente = "-"
nombre_binario = "-"
#
#--------------------------------------------------------------------------------------------------------------
# bool2chr: convierte True a "O" y False a "X"
#--------------------------------------------------------------------------------------------------------------
def bool2chr(val):
  return "O" if val else "X"
#
#--------------------------------------------------------------------------------------------------------------
# msg_error: muestra un mensaje de error, es decir, letra roja sobre fondo negro estandar. Si es, ademas,
# un error fatal o catastrofico en el programa, se termina la ejecucion del programa inmediatamente.
#--------------------------------------------------------------------------------------------------------------
def msg_error(texto, fatal):
  print(f"\033[31mError: {texto}.\033[0m")
  if fatal:
    sys.exit(1)
#
#--------------------------------------------------------------------------------------------------------------
# msg_note: muestra un mensaje tipo warning, es decir, letra verde sobre el fondo estandar (negro). Nada mas.
#--------------------------------------------------------------------------------------------------------------
def msg_note(texto):
  print(f"\033[32m{texto}.\033[0m")
#
#--------------------------------------------------------------------------------------------------------------
# ping: realiza la prueba de conexion a la IP recibida como argumento.
#--------------------------------------------------------------------------------------------------------------
def ping(nodo):
    return os.system(f"ping -c 1 {nodo} > /dev/null 2>&1")
#
#--------------------------------------------------------------------------------------------------------------
# ejecutar_shell: utiliza subprocess para ejecutar un comando del sistema. Recibe flag quiet (indica que la
# ejecucion del comando debe ser silenciosa, sin hacer eco en pantalla del comando), imprime (indica que la
# salida del comando debe ser impresa cuando quiet=True), importante (indica que el comando es mas importante y
# debe ser impreso en color celeste en vez del violeta usual).
#--------------------------------------------------------------------------------------------------------------
def ejecutar_shell(comando, quiet, imprime, importante):
  atrib = 35 if not importante else 36
  if not quiet:
    print(f"\033[{atrib}m@ {comando}\033[33m")

  salida = subprocess.getoutput(comando)

  if not quiet and imprime:
    print(f"{salida}\033[0m")

  return salida
#
#--------------------------------------------------------------------------------------------------------------
# check_lam: verifica que el proceso lam.d este activo en el nodo maestro. Para eso revisa la salida del
# comando lamnodes ejecutado en el maestro. Si lam.d no esta activo, entonces la salida empieza con "-". La
# funcion devuelve True si LAM esta activo o False si no lo esta.
#--------------------------------------------------------------------------------------------------------------
def check_lam():
  salida = ejecutar_shell(f"rsh {maestro} lamnodes", True, False, False)
  return ('-' not in salida)
#
#--------------------------------------------------------------------------------------------------------------
# leer_nombre_nodo: lee de teclado la IP/nombre de un nodo (no valida nada)
#--------------------------------------------------------------------------------------------------------------
def leer_nombre_nodo():
  nodo = input("Introduzca nombre/direccion IP: ")
  return nodo
#
#--------------------------------------------------------------------------------------------------------------
# leer_nro_nodo: lee de teclado el numero "nX" de un nodo (en formato cadena, no valida nada)
#--------------------------------------------------------------------------------------------------------------
def leer_nro_nodo():
  nodo = input("Introduzca identificador de nodo: ")
  return nodo
#
#--------------------------------------------------------------------------------------------------------------
# load_default: carga lista de nodos por defecto (los nodos "alfa")
#--------------------------------------------------------------------------------------------------------------
def load_default():
  global nodos
  global maestro
  for i in range(5):
    test = not ping(f"alfa0{i}")
    maestro = f"alfa0{i}" if maestro == "-" and test else maestro
    nodos.append([f"n{i}", f"alfa0{i}", (True and test), test])
#
#--------------------------------------------------------------------------------------------------------------
# cargar_nodos: carga la lista de nodos del archivo de configuracion indicado en el argumento. Ignora todas las
# lineas de comentarios (arrancan con "#") y realiza las pruebas de conexion en cada nodo. El primer nodo que
# pase la prueba del ping va a ser asignado como maestro y va a tener el campo SEL en True siempre. Los demas
# nodos van a tener SEL=True. Cualquier demora en la respuesta es por el timeout del ping. De fallar esta
# prueba, se marcara al nodo como offline.
#--------------------------------------------------------------------------------------------------------------
def cargar_nodos(archivo):
    global maestro
    global nodos

    if not os.path.exists(archivo):
       msg_error("El archivo de configuracion no existe", True)

    i = 0

    with open(archivo, "r") as f:
        for l in f:
            l = l.strip()
            if not l.startswith("#") and l:
                offline = ping(l)
                maestro = l if (maestro == "-" and not offline) else maestro
                nodos.append([f"n{i}", l, (True and not offline), not offline])
                i = i+1
                
    if not nodos:
        msg_error("Listado invalido", True)

    return nodos
#
#--------------------------------------------------------------------------------------------------------------
# guardar_lamhosts: recorre la lista de nodos y arma un archivo temporal para iniciar el LAM usando solo los
# nodos que esten online y con el campo SEL=True. Es un archivo de texto plano con los nombres de los nodos.
#--------------------------------------------------------------------------------------------------------------
def guardar_lamhosts():
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        for nodo in nodos:
            if nodo[2]:
                f.write(nodo[1] + '\n')		# Guarda el nombre/IP del nodo seleccionado
        return f.name
#
#--------------------------------------------------------------------------------------------------------------
# listar_nodos: arma y muestra una lista de los nodos en pantalla, incluyendo aquellos que estan offline y los
# que no estan seleccionados (basicamente, son los nodos del archivo de texto ignorando los comentarios). Se
# muestra en video inverso al nodo maestro y los siguientes campos, separados con tabulaciones:
#   nro_nodo        numero del nodo dentro del cluster (n0..nX)
#   nombre/IP       nombre o direccion IP del nodo
#   seleccionado    muestra "O" si es parte del cluster o "X" si no lo es
#   online          muestra "O" si el nodo es accesible/esta conectado a la red, o "X" si no lo es (falla ping)
#--------------------------------------------------------------------------------------------------------------
def listar_nodos():
  print("\n\033[0mListado de nodos:\n"+"-"*40)
  for nodo in nodos:
    attrib = "32" if nodo[2] else "37"
    sys.stdout.write(f"\t\033[7;{attrib}m") if maestro == nodo[1] else sys.stdout.write(f"\t\033[0;{attrib}m")
    print(f"{nodo[0]:<3}  {nodo[1]:<10}  [{bool2chr(nodo[2])}]  [{bool2chr(nodo[3])}]\033[0m")
  print("-"*40)
#
#--------------------------------------------------------------------------------------------------------------
# iniciar_lamboot: arma el archivo de configuracion lamhosts y lo envia al nodo maestro, para luego ejecutar el
# comando "lamboot -v lamhosts". Valida que haya un nodo maestro seleccionado y que LAM no este activo.
#--------------------------------------------------------------------------------------------------------------
def iniciar_lamboot():
  if maestro == "-":
    msg_error("Nodo maestro indeterminado", False)
    return
    
  if check_lam():
    msg_note(f"LAM ya esta activo en {maestro}")
    return

  lamhosts_path = guardar_lamhosts()

  # Copiar el lamhosts al maestro e invocar lamboot -v lamhosts
  ejecutar_shell(f"rcp {lamhosts_path} {maestro}:{home_dir}/lamhosts", False, False, False)
  ejecutar_shell(f"nohup rsh {maestro} lamboot -v {home_dir}/lamhosts > /dev/null 2>&1 &", False, False, False)

  # Esperar 5 segundos para darle tiempo al cluster para iniciar
  time.sleep(10)

  # Listar los nodos en pantalla
  ejecutar_shell(f"rsh {maestro} lamnodes", False, True, False)

  # Eliminar el archivo temporal
  os.remove(lamhosts_path)

  return
#
#--------------------------------------------------------------------------------------------------------------
# chau_lam: detiene el entorno LAM, si esta activo
#--------------------------------------------------------------------------------------------------------------
def chau_lam():
  if maestro != "-":
    if check_lam():
      ejecutar_shell(f"rsh {maestro} lamhalt", False, True, False)
    else:
      msg_note(f"LAM inactivo")
  else:
    msg_error("Nodo maestro indeterminado", False)
#
#--------------------------------------------------------------------------------------------------------------
# imprimir_estado: imprime el estado del cluster. Nada sofisticado, solo hace la prueba del lamnodes e imprime
# el nodo donde esta corriendo, si esta corriendo, o avisa que esta inactivo o que el nodo maestro no existe.
#--------------------------------------------------------------------------------------------------------------
def imprimir_estado():
  if maestro == "-":
    msg_error("Nodo maestro indeterminado", False)
  else:
    if check_lam():
      msg_note(f"LAM activo en {maestro}")
    else:
      msg_note("LAM inactivo")
#
#--------------------------------------------------------------------------------------------------------------
# set_maestro: recorre la lista de nodos y agarra el primer nodo online como maestro, y activa el campo SEL.
#--------------------------------------------------------------------------------------------------------------
def set_maestro():
  global maestro

  for n in nodos:
    if n[3]:
      maestro = n[1]
      n[2] = True
    break
#
#--------------------------------------------------------------------------------------------------------------
# swap_nodos: realiza el intercambio de dos nodos recibidos como argumentos. Valida que existan y que LAM este
# inactivo antes de realizar la operacion (sino lo mata).
#--------------------------------------------------------------------------------------------------------------
def swap_nodos(n1, n2):
  global nodos
  global maestro
  
  # Procesar la entrada, verificar que sea valida
  
  try:
    nro1 = int(''.join(filter(str.isdigit, n1)))
    nro2 = int(''.join(filter(str.isdigit, n2)))
  except:
    msg_error("Entrada invalida", False)
    return
    
  if nro1 > len(nodos)-1 or nro2 > len(nodos)-1:
    msg_error("Nodo invalido", False)
    return

  lo_mate = False                 # Hace falta apagar LAM?
  con_maestro = (maestro != "-")  # Esta definido el nodo maestro?
    
  if con_maestro:
    #msg_error("Nodo maestro indefinido", False)
    #return
    
    # Ver si LAM esta activo
    if check_lam():
      ejecutar_shell(f"rsh {maestro} lamhalt", False, False, False)
      lo_mate = True

  # Realizar intercambio
  
  aux = nodos[nro1]
  auxn = nodos[nro1][0]
  
  nodos[nro1][0] = nodos[nro2][0]
  nodos[nro2][0] = auxn
  
  nodos[nro1] = nodos[nro2]
  nodos[nro2] = aux
  
  # Si LAM tuvo que ser detenido, lo tengo que reiniciar
  if lo_mate:
    iniciar_lamboot()

  # Si el maestro no existe, tengo que definir uno nuevo
  if not con_maestro:
    set_maestro()
#
#---------------------------------------------------------------------------------------------------------------
# reasignar_maestro: hace que un nodo especifico sea el maestro, a diferencia del reemplazo automatico. Si LAM
# estuviese activo, se lo detiene porque si o si se va a tener que reordenar los nodos manualmente para que se
# mantenga la correlacion entre el id del nodo en la lista y en el archivo lamhosts.
#---------------------------------------------------------------------------------------------------------------
def reasignar_maestro(n):
  global maestro

  # Procesar la entrada, verificar que sea valida
  try:
    nro = int(''.join(filter(str.isdigit, n)))
  except:
    msg_error("Entrada invalida", False)
    return

  if nro > len(nodos)-1:
    msg_error("Nodo invalido", False)
    return

  if not nodos[nro][3]:
    msg_error("Nodo offline", False)
    return

  lo_mate = False

  if check_lam():
    ejecutar_shell(f"rsh {maestro} lamhalt", False, False, False)
    lo_mate = True

  #swap_nodos("n0",n)

  maestro = nodos[nro][1]
  nodos[0][2] = True
  
  swap_nodos("n0",n)

  if lo_mate:
    iniciar_lamboot()
#
#--------------------------------------------------------------------------------------------------------------
# menu de configuracion del cluster
#--------------------------------------------------------------------------------------------------------------
def estado_del_cluster():

  global maestro

  listar_nodos()
  imprimir_estado()

  while True:
    print("\n\033[0m  1. Reordenar nodos")
    print("  2. Agregar nodo")
    print("  3. Remover nodo")
    print("  4. Cambiar estado de nodo")
    print("  5. Reasignar maestro\n")
    print("  0. Terminar y volver al menu\n")

    opcion = input("\033[4mElige una opcion:\033[0m ")

    if opcion == "1":
      swap_nodos(leer_nro_nodo(),leer_nro_nodo())
    elif opcion == "2":
      agregar_nodo(leer_nombre_nodo())
    elif opcion == "3":
      quitar_nodo(leer_nro_nodo())
    elif opcion == "4":
      seleccionar(leer_nro_nodo())
    elif opcion == "5":
      reasignar_maestro(leer_nro_nodo())
    elif opcion == "0":
      break
    else:
      msg_error("Entrada incorrecta", False)

    listar_nodos()
    imprimir_estado()
#
#--------------------------------------------------------------------------------------------------------------
# puedo_encolar: me devuelve True si estoy en condiciones de encolar trabajo/compilar remoto, False cc.
#--------------------------------------------------------------------------------------------------------------
def puedo_encolar():
  puedo = True
  
  if maestro == "-":
    msg_error("Nodo maestro indeterminado", False)
    puedo = False
  elif not check_lam():
    msg_error(f"LAM inactivo en {maestro}", False)
    puedo = False
    
  return puedo
#
#--------------------------------------------------------------------------------------------------------------
# compilar_job: recibe la ruta a un archivo fuente *.c, lo copia al nodo maestro y compila con hcc.
#--------------------------------------------------------------------------------------------------------------
def compilar_job():
  global nombre_fuente
  global nombre_binario
  
  ruta_fuente = input("Archivo fuente (sin extension): ")
  
  if not os.path.exists(f"{ruta_fuente}.c"):
    msg_error(f"El archivo {ruta_fuente}.c no existe", False)
    return False
    
  # Agregar timestamp al nombre del binario
  timestamp = subprocess.check_output("date +%Y%m%d%H%M%S", shell=True).decode().strip()
  nombre_fuente = f"{os.path.basename(ruta_fuente)}_{timestamp}"
  nombre_binario = nombre_fuente

  ejecutar_shell(f"rcp {ruta_fuente}.c {maestro}:{home_dir}/{nombre_fuente}.c", False, False, False)
  
  # Compilar el programa. Si falla, imprime la salida y elimina

  salida = ejecutar_shell(f"rsh {maestro} hcc -o {home_dir}/{nombre_binario} {home_dir}/{nombre_fuente}.c -lm", False, False, True)
  
  # Imprime la salida del compilador. Si contiene la palabra "error", se elimina todo archivo relacionado al codigo que fallo
  # De esta forma se consigue que, si es un warning, lo deje pasar
  
  print(salida)
  hay_error = (salida.upper()).find("ERROR")
  
  if hay_error != -1:
    print(hay_error)
    ejecutar_shell(f"rsh {maestro} rm {home_dir}/{nombre_binario}*", False, False, True)
    return False
    
  return True
#
#--------------------------------------------------------------------------------------------------------------
# copiar_binario: realiza la copia del archivo binario a todos los nodos del cluster
#--------------------------------------------------------------------------------------------------------------
def copiar_binario():
  if nombre_binario == "-":
    msg_error("No existe archivo binario", False)
    return False
    
  for nodo in nodos:
    if nodo[1] != maestro and nodo[2]:
      ejecutar_shell(f"rsh {maestro} rcp {home_dir}/{nombre_binario} {nodo[1]}:{home_dir}/", False, False, False)
      
  return True
#
#--------------------------------------------------------------------------------------------------------------
# ejecutar_job: copia el binario a cada uno de los nodos (seleccionados Y online, revisa ambos) e invoca el
# comando mpirun C con las opciones recibidas. Luego, borra todos los archivos en los nodos (limpieza).
#--------------------------------------------------------------------------------------------------------------
def ejecutar_job():
  global nombre_binario
  
  if nombre_binario == "-":
    msg_error("Compile antes de ejecutar", False)
    return
    
  if not copiar_binario():
    return
      
  args = input("Argumentos del programa (opcionales): ")      
  ejecutar_shell(f"rsh {maestro} mpirun C {home_dir}/{nombre_binario} {args}", False, True, True)
    
  for nodo in nodos:
    if nodo[2]:
      ejecutar_shell(f"rsh {nodo[1]} rm -f {home_dir}/{nombre_binario}*", False, False, False)
      
  nombre_binario = "-"
#
#--------------------------------------------------------------------------------------------------------------
# enviar_y_compilar_trabajo: compila, copia y manda a ejecutar un trabajo completo usando las funciones
# modulares implementadas.
#--------------------------------------------------------------------------------------------------------------
def enviar_y_compilar_trabajo():
    if not compilar_job():
      msg_error("Hubo un problema al compilar el programa", False)
      return
          
    ejecutar_job()

#
#--------------------------------------------------------------------------------------------------------------
# agregar_nodo: recibe el nombre/IP de un equipo y, si pasa la prueba de conectividad y no esta en el cluster,
# lo agrega a la lista de nodos con SEL=True y lo agrega al LAM si esta activo.
#--------------------------------------------------------------------------------------------------------------
def agregar_nodo(nuevo):
  if ping(nuevo):
    msg_error(f"La direccion {nuevo} no es valida", False)
    return

  i = 0
  ya_esta = False

  for nodo in nodos:
    if nodo[1] == nuevo:
      ya_esta = True
      break
    i = i+1

  if ya_esta:
    msg_error(f"{nuevo} ya es parte del cluster", False)
    return

  nodos.append([f"n{i}", nuevo, True, not ping(nuevo)])
  
  if maestro == "-":
    msg_error("Nodo maestro indeterminado", False)
    return
  
  if check_lam():
    ejecutar_shell(f"rsh {maestro} lamgrow -n {i} {nuevo}", False, False, False)
  else:
    msg_note(f"LAM inactivo en {maestro}")
#
#--------------------------------------------------------------------------------------------------------------
# quitar nodo: recibe un numero de nodo en formato cadena. Si es un numero valido y si esta LAM activo, invoca
# lamshrink para remover el nodo del cluster. Si, ademas, no es el ultimo de la lista, lo marca como INVALIDO.
# Si no esta activo, lo quita de la lista, este o no activo el cluster.
#--------------------------------------------------------------------------------------------------------------
def quitar_nodo(borrar):
  global nodos
  global maestro
  
  # Procesar la entrada, verificar que sea valida
  
  try:
    nro = int(''.join(filter(str.isdigit, borrar)))
  except:
    msg_error("Entrada invalida", False)
    return
    
  # Ver que haya un maestro
    
  if maestro == "-":
    msg_error("Nodo maestro indeterminado", False)
    return
    
  # Ver que haya al menos dos nodos para poder borrar
    
  if len(nodos) == 1:
    msg_note("Hay un unico nodo")
    return

  if nro > len(nodos)-1:
    msg_error("Nodo invalido", False)
    return
  
  # Si justo es el maestro Y LAM esta activo, lo voy a tener que apagar
  # Despues, borro el nodo sin culpa, reasigno las posiciones y reinicio LAM
  if maestro == nodos[nro][1]:
    lo_mate = False

    if check_lam():
      # Aca voy a tener que parar el LAM, borrar el nodo, reasignar maestro y reiniciar
      ejecutar_shell(f"rsh {maestro} lamhalt", False, False, False)
      lo_mate = True

    nodos.remove(nodos[nro])
    for i in range(nro,len(nodos)):
      ant = int(''.join(filter(str.isdigit, nodos[i][0])))-1
      nodos[i][0] = f"n{ant}"

    set_maestro()
    if lo_mate:
      iniciar_lamboot()
    return

  else:
    lo_mate = False
    if check_lam():
      ejecutar_shell(f"rsh {maestro} lamhalt", False, False, False)
      lo_mate = True

    nodos.remove(nodos[nro])
    for i in range(nro, len(nodos)):
      ant = int(''.join(filter(str.isdigit, nodos[i][0])))-1
      nodos[i][0] = f"n{ant}"

    if lo_mate:
      iniciar_lamboot()
      
    return

# Seleccionar nodos
def seleccionar(nodo):
  global nodos
  global maestro

  #if nodo == "*":
  #  msg_note("Se quiere habilitar todos los nodos.")
  #  return
  
  try:
    n = int(''.join(filter(str.isdigit, nodo)))
  except:
    msg_error("Entrada invalida", False)
    return

  if n > len(nodos)-1:
    msg_error("Nodo invalido", False)
    return

  lo_mate = False

  if maestro == nodos[n][1]:
    if check_lam():
      ejecutar_shell(f"rsh {maestro} lamhalt", True, True, False)
      lo_mate = True

    nodos[n][2] = not nodos[n][2]

    # El que deshabilite era el maestro... busco uno nuevo (si se puede)
    for n in nodos:
      if n[1] != maestro and n[3] and n[2]:
        maestro = n[1]
        n[2] = True
        break
        
    # Me fijo si el maestro quedo seleccionado o no. Si no, lo habilito yo a mano
    # Esto es para que no quede un nodo maestro indeterminado y el usuario pueda causar problemas
    for n in nodos:
        if n[1] == maestro and not n[2]:
            n[2] = True

    # Si tuve que terminar LAM, lo reinicio
    if lo_mate:
      iniciar_lamboot()

    return

  if nodos[n][1] == "INVALIDO":
    msg_error("Nodo invalido", False)
    return

  if not nodos[n][3]:
    msg_error("Nodo offline",False)
    return

  nodos[n][2] = not nodos[n][2]
  
  if maestro == "-" and nodos[n][2]:
    maestro = nodos[n][1]
    return

  if check_lam():
    if nodos[n][2]:
      ejecutar_shell(f"rsh {maestro} lamgrow -n {n} {nodos[n][1]}", False, False, False)
    else:
      ejecutar_shell(f"rsh {maestro} lamshrink {nodos[n][0]}", False, False, False)
    ejecutar_shell(f"rsh {maestro} lamnodes", False, True, False)

# Programa principal
def main():
    archivo_nodos = sys.argv[1] if len(sys.argv) > 1 else "nodes"

    if len(sys.argv) <= 1:
        msg_note("Usando configuracion por defecto")
        load_default()
    else:
      msg_note("Cargando lista de nodos..")
      cargar_nodos(archivo_nodos)
      
    msg_note(f"Nodo maestro: {maestro}")

    if check_lam():
        msg_note("Hay una sesion previa de LAM abierta, finalizando LAM..")
        ejecutar_shell(f"rsh {maestro} lamhalt", True, False, False)

    while True:
        print("\n\033[0m" + "="*40 + "\n" + " "*4 + "W O R K L O A D   M A N A G E R" + "\n" + "="*40)
        print("  1. Configuracion del cluster")
        print("  2. Iniciar LAM")
        print("  3. Terminar LAM")
        print("\n  4. Compilar fuente")
        print("  5. Copiar binario")
        print("  6. Ejecutar")
        print("\n  7. Compilar y ejecutar programa")
        print("\n  0. Salir\n" + "="*40)

        opcion = input("\033[4mElige una opcion:\033[0m ")

        if opcion == "1":
            estado_del_cluster()
        elif opcion == "2":
            iniciar_lamboot()
        elif opcion == "3":
            chau_lam()
        elif opcion == "4":
          if puedo_encolar():
            compilar_job()
        elif opcion == "5":
          if puedo_encolar():
            copiar_binario()
        elif opcion == "6":
          if puedo_encolar():
            ejecutar_job()
        elif opcion == "7":
          if puedo_encolar():
            enviar_y_compilar_trabajo()
        elif opcion == "0":
          chau_lam()
          break
        else:
            msg_error("Entrada incorrecta", False)

if __name__ == "__main__":
    main()
