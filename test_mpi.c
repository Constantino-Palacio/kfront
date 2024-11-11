/* Calculo de PI usando el metodo de Montecarlo en un cluster */
/**
 * @author anizz, nicks
 */

// Modificado por Constantino Palacio, 2024.

#include<stdio.h>
#include<stdlib.h>
#include<math.h>
#include<time.h>
#include<mpi.h>

int main(int argc, char *argv[]) {
	int rank, size;
	long int i, j, n;
	clock_t ini, fin;
	float x, y, d, pi, pi_, pii;
	FILE *archivo;

	j = 0;

	MPI_Init(&argc, &argv);
	MPI_Comm_size(MPI_COMM_WORLD, &size);
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);

	srand((unsigned)time(NULL) + rank);

	if (rank == 0) {
		n = 12000000/size;
		ini = clock();
	}

	MPI_Bcast(&n, 1, MPI_INT, 0, MPI_COMM_WORLD);

	for (i=0; i<n; i++) {
		x = (double)rand() / RAND_MAX;
		y = (double)rand() / RAND_MAX;
		d = sqrt(x*x + y*y);
		if (d <= 1.0) j++;
	}

	pi = 4.0 * j/n;
	printf("%f en nodo %d con %ld puntos.\n", pi, rank, n);

	MPI_Reduce(&pi, &pi_, 1, MPI_FLOAT, MPI_SUM, 0, MPI_COMM_WORLD);

	if (rank == 0) {
		pii = (double)pi_ / size;
		fin = clock();
		printf("PI= %f (promedio) en %f seg en %d procesadores.\n", pii, (double) (fin-ini)/CLOCKS_PER_SEC, size);
	}

	MPI_Finalize();
	return 0;
}

