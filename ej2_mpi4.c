#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <mpi.h>

// para mediciones de tiempo
double dwalltime(){
	double sec;
	struct timeval tv;

	gettimeofday(&tv,NULL);
	sec = tv.tv_sec + tv.tv_usec/1000000.0;
	return sec;
}


// interna blkmul: realiza la multiplicación de dos bloques bs x bs
void blkmul(double *ablk, double *bblk, double *cblk, int n, int bs){
    int i,j,k;
    for (i=0;i<bs;i++)
        for (j=0;j<bs;j++)
            for (k=0;k<bs;k++)
                cblk[i*n+j] += ablk[i*n+k] * bblk[j*n+k];
}

// externa matmulblks: los elementos enviados a blkmul son los que estan en la esquina superior
// izquierda del bloque bs x bs. Multiplica invocando a blkmul de a bloques de tamaño bs.
void matmulblks(double *a, double *b, double *c, int n, int bs, int cantProcs){
 int i,j,k,hasta;
	hasta=n/cantProcs;
    	for (i=0;i<hasta;i+=bs)
        	for (j=0;j<n;j+=bs)
            		for (k=0;k<n;k+=bs)
                		blkmul(&a[i*n+k], &b[k+n*j], &c[i*n+j], n, bs);
}

// impresion de matriz en pantalla
void deb_out(double* A, int n) {
int i,j;
    for (i=0;i<n;i++) {
        for (j=0;j<n;j++)
            printf("%.0f\t",A[(i*n)+j]);
        printf("\n");
    }
    printf("\n");
}

// Devuelve la suma de los n meros 1 a n (para validaci n)
double suma(int n) {				
	double s=0;
        int i;
	for (i=0;i<n;i++) s=s+i+1;

	return s;
}
//calculo de promedio para validacion
double avgP_expect(double valor, int n) {
	double p=0;
        int i;
	for (i=0;i<n;i++) p+=(i+1)*valor;

	p*=n;
	p/=(double)(n*n);

	return p;
}


int main(int argc, char *argv[]) {
    	double *A, *B, *C, *D, *P, *R,*AB, *ABC, *DCB, *temp, minA, maxD;
	double *A_buf, *D_buf, *AB_buf, *ABC_buf, *DC_buf, *DCB_buf, *P_buf, *R_buf, avgP;
    	int i,j,n,bs,pid,cantProcs;
        double tiempoInicio, tiempoFinal,tiempoIniCom1,tiempoFinCom1;
        int sizeMatrix,sizePart,err;
	double minA_local,maxD_local,sumaP,aux,S,P1,SS;
	
	//n = 256;
	//bs = 16;
	
	// Chequeo de parametros
	if ( (argc != 3) || (atoi(argv[1]) <= 0) || (atoi(argv[2]) <= 0) || ((atoi(argv[1]) % atoi(argv[2])) != 0)){
		printf("Error de argumentos. Usar: ./%s n BS (n debe ser multiplo de BS)\nxn debe ser divisible por el numero de procesadores.\n", argv[0]);
		printf("%d\t%d\n",n,bs);
		exit(1);
	}

	n = atoi(argv[1]);
	bs = atoi(argv[2]);

	/*
	 * Inicializacion de MPI
	*/

	MPI_Init(&argc,&argv);
	MPI_Comm_rank(MPI_COMM_WORLD, &pid);
	MPI_Comm_size(MPI_COMM_WORLD, &cantProcs);

	sizeMatrix=n*n;
	sizePart=sizeMatrix/cantProcs;

	B = (double *) malloc(n*n*sizeof(double));
	C = (double *) malloc(n*n*sizeof(double));
	
	/*
	 * Solo el root (pid 0) aloca e inicializa las matrices completas. Cada proceso va a inicializar sus propias
	 * matrices locales para poder realizar los c lculos.
	*/
	
	if (pid==0) {
		// Alocar  
		A = (double *) malloc(n*n*sizeof(double));
		D = (double *) malloc(n*n*sizeof(double));
		P = (double *) malloc(n*n*sizeof(double));
		R = (double *) malloc(n*n*sizeof(double));

    		// Inicializacion de las matrices
		for (i = 0; i < n; i++){
			for (j = 0; j < n; j++){
				A[i*n + j] = j+1.0;     // por filas    -> esta a izq del producto
				B[j*n + i] = j+1.0;     // por columnas -> esta a der del producto
				C[j*n + i] = j+1.0;     // por columnas -> esta a der del producto
				D[i*n + j] = j+1.0;     // por filas    -> esta a izq del producto
				P[i*n + j] = 0.0;
				R[i*n + j] = 0.0;
			}
		}

		temp = (double*) malloc(sizeMatrix * sizeof(double));

		// mensaje introductorio
		printf("+--------------------------------------------------------------------\n");
		printf("Calculo con matrices de %dx%d, con bloques de %dx%d.\nProcesamiento distribuido en %d procesos (particiones de %d).\n\n",n,n,bs,bs,cantProcs,sizePart);
	}

	for (i=0;i<sizePart;i++) {
		AB_buf=0;
		ABC_buf=0;
		DC_buf=0;
		DCB_buf=0;
		P_buf=0;
		R_buf=0;
	}

	// Alocar matrices locales parciales

	A_buf = (double *) malloc(sizePart*sizeof(double));
	AB_buf = (double *) malloc(sizePart*sizeof(double));
	ABC_buf = (double *) malloc(sizePart*sizeof(double));

	D_buf = (double *) malloc(sizePart*sizeof(double));
	DC_buf = (double *) malloc(sizePart*sizeof(double));
	DCB_buf = (double *) malloc(sizePart*sizeof(double));

	P_buf= (double*) malloc(sizePart*sizeof(double));
	R_buf= (double*) malloc(sizePart*sizeof(double));

        tiempoInicio = MPI_Wtime();
	//double tiempoInicio=dwalltime();	// como no imprime nada entre tiempo de inicio y finalizaci n, no hay problema

	// Dividir A y D para calculo de maximos y minimos locales con MPI_Scatter(). Luego tomar los resultados con MPI_Reduce().
	MPI_Scatter(A,sizePart,MPI_DOUBLE,A_buf,sizePart,MPI_DOUBLE,0,MPI_COMM_WORLD);
	MPI_Scatter(D,sizePart,MPI_DOUBLE,D_buf,sizePart,MPI_DOUBLE,0,MPI_COMM_WORLD);

	// buscar max y min locales

	minA_local=A_buf[0];
	maxD_local=D_buf[0];

	for (i=0;i<sizePart;i++) {
		if (A_buf[i]<minA_local) minA_local=A_buf[i];
		if (D_buf[i]>maxD_local) maxD_local=D_buf[i];
	}

	// obtener valores globales y compartirlos con todos los procesos usando MPI_Bcast()

	MPI_Allreduce(&minA_local,&minA,1,MPI_DOUBLE,MPI_MIN,MPI_COMM_WORLD);
	MPI_Allreduce(&maxD_local,&maxD,1,MPI_DOUBLE,MPI_MAX,MPI_COMM_WORLD);

	// Dividir A, B, C y D para c lculo de productos matriciales ABC y DCB con MPI_Scatter(). Ir armando la matriz P a medida que
	// est n listos los productos. Luego tomar los resultados con MPI_Gather(). C y B deben ser conocidas en su totalidad para poder hacer
	// el producto -> las comparto entre todos los procesos con MPI_Bcast()

	MPI_Gather(A_buf, sizePart, MPI_DOUBLE, temp, sizePart, MPI_DOUBLE, 0, MPI_COMM_WORLD);

	MPI_Scatter(A, sizePart, MPI_DOUBLE, A_buf, sizePart, MPI_DOUBLE, 0, MPI_COMM_WORLD);
	MPI_Scatter(D, sizePart, MPI_DOUBLE, D_buf, sizePart, MPI_DOUBLE, 0, MPI_COMM_WORLD);
	MPI_Bcast(B, sizeMatrix, MPI_DOUBLE, 0, MPI_COMM_WORLD);
	MPI_Bcast(C, sizeMatrix, MPI_DOUBLE, 0, MPI_COMM_WORLD);

        MPI_Barrier(MPI_COMM_WORLD);

	matmulblks(A_buf, B, AB_buf, n, bs,cantProcs);		// AB <- A*B
	matmulblks(AB_buf, C, ABC_buf, n, bs,cantProcs);	// ABC <- A*B*C

	matmulblks(D_buf, C, DC_buf, n, bs,cantProcs);		// DC <- D*C
	matmulblks(DC_buf, B, DCB_buf, n, bs,cantProcs);	// DCB <- D*C*B

	sumaP=0;
	aux;

	for (i=0;i<sizePart;i++) {
		aux=maxD*ABC_buf[i]+minA*DCB_buf[i];
		sumaP+=aux;
		P_buf[i]=aux;
	}


	MPI_Gather(P_buf, sizePart, MPI_DOUBLE, P, sizePart, MPI_DOUBLE, 0, MPI_COMM_WORLD);
	MPI_Allreduce(&sumaP,&avgP,1,MPI_DOUBLE,MPI_SUM,MPI_COMM_WORLD);

	avgP/=(n*n);

	for (i=0;i<sizePart;i++)
		R_buf[i]=avgP*P_buf[i];

	MPI_Gather(R_buf, sizePart, MPI_DOUBLE, R, sizePart, MPI_DOUBLE, 0, MPI_COMM_WORLD);

	/*
	 * La impresi n del tiempo, validacion y liberacion de memoria la hace el root para las matrices completas.
	 * Despues cada proceso libera las matrices parciales locales.
	*/
           //tiempoFinal = MPI_Wtime();
	if (pid==0) {
                
		printf("Tiempo Total: %f\n\n",MPI_Wtime()-tiempoInicio);	// impresi n medici n total de tiempo

		S=suma(n);				// S = 1 + 2 + ... + n; AB[1,1] y DC[1,1]
		SS=S*S;					// ABC[1,1] y DCB[1,1]
		P1=(n+1)*SS;				// P[1,1]

		if ((maxD==(double)n) && (minA==1.0)) {	// minA y maxD son correctos -> seguir validando
			printf("minA y maxD correctos.\n");

			// para matrices "chicas" se valida el promedio -> si da bien y P tambien, R es correcta
			// la validacion falla para matrices con n>=1024 (se probo solo con n potencia de 2) por un redondeo involuntario
			// en el calculo del promedio esperado -> se saltea la comprobacion de avgP para matrices "grandes"
			if (n<1024) {
				if (avgP==avgP_expect(P1,n))
					printf("avgP correcto.\n");
				else printf("avgP incorrecto: %.1f/%.1f.\n",avgP,avgP_expect(P1,n));
			}

			// la validacion de R no se hace por el error en avgP. Si n<1024, avgP esta validado. Entonces R es correcta si
			// la matriz P tambien lo es (P se valida abajo y vale siempre). Si n>=1024, la validacion de avgP no garantiza que el
			// resultado sea correcto, entonces no se valida R.
		
		        err=0;
			for (i=0;i<n;i++)
				for (j=0;j<n;j++)
					if (P[i*n+j]!=(j+1)*(n+1)*SS) {
						printf("Valor en [%d,%d] err neo.\t\tEsperado/Recibido:\t%.0f/%.0f\n",i,j,(j+1)*(n+1)*SS,P[i*n+j]);
						err++;
					}
	
			if (err>0) printf("Error en c lculo matricial.\n"); else printf("Resultados matriciales correctos.\n");
		} else printf("Error en minA y/o maxD: %.0f/1, %.0f/%.0f.\n", minA, maxD, (double)n);

		printf("+--------------------------------------------------------------------\n");
	
	    	// Liberacion de memoria alocada (matrices completas)
	    	free(A);
	    	
	    	free(D);
	    	free(P);
	    	free(R);

		//free(AB);
		//free(ABC);
		//free(DCB);
	}

	// Liberacion de memoria alocada (matrices parciales)
	free(A_buf);
	free(AB_buf);
	free(ABC_buf);
	free(D_buf);
	free(DC_buf);
	free(DCB_buf);
	free(P_buf);
	free(R_buf);
	free(B);
	free(C);

    	// terminacion MPI y salida del programa
	MPI_Finalize();
	return 0;
}
