#include "fsout.h"

FSout *gpfgout;
FSout *gpnbout;


FSout::FSout(char *filename)
{
	out = fopen(filename,"wt");
}

FSout::~FSout()
{
	if(out)
		fclose(out);
}

int FSout::isOpen()
{
	if(out)
		return 1;
	else
		return 0;
}

void FSout::printSet(int length, int *iset, int support)
{
	fprintf(out, "%d ", length);
	for(int i=0; i<length; i++) 
		fprintf(out, "%d ", iset[i]);
	fprintf(out, "%d\n", support);
}

void FSout::printFBdSet(int length, int* iset, int support, int nrdnt_item)
{
	fprintf(out, "%d ", length);
	fprintf(out, "%d ", nrdnt_item);
	for(int i=0;i<length;i++)
	{
		if(iset[i]!=nrdnt_item)
			fprintf(out, "%d ", iset[i]);
	}
	fprintf(out, "%d\n", support);
}
