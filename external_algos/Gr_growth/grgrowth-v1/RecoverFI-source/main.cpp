#define _CRTDBG_MAP_ALLOC
#include <stdlib.h>
#include <crtdbg.h>
#include <errno.h>

#include <stdio.h>
#include <string.h>
#include "global.h"

int gnrep_type;

int main(int argc, char* argv[])
{
	int i;

	if(argc!=4 && argc!=5)
	{
		i = strlen(argv[0])-1;
		while(i>=0 && argv[0][i]!='\\')
			i--;
		i++;
		printf("Usage:\n");
		printf("  %s freqkey_filename border_filename coveritem_filename [output_filename]\n\n", &(argv[0][i]));
		return 0;		
	}

	if(strcmp(argv[3], "NULL") && strcmp(argv[3], "null"))
		gnrep_type = 1;
	else
		gnrep_type = 0;

	if(argc==5)
		RecoverFI(argv[1], argv[2], argv[3], argv[4]);
	else
		RecoverFI(argv[1], argv[2], argv[3], NULL);

	_CrtDumpMemoryLeaks();

	return (int)gdtotal_pats;
}

