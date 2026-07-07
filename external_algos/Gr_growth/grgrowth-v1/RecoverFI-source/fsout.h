#pragma once 

#include <stdio.h>
#include "global.h"

class FSout
{
public:

	FSout(char *filename);
	~FSout();
	int isOpen();
	void printSet(int length, int *iset, int support);

private:
	FILE *out;
};

extern FSout *gpfout;

inline void OutputOnePat(int nsupport)
{

	gdtotal_pats++;
	if(gnmax_pat_len<gnprefix_len)
		gnmax_pat_len = gnprefix_len;

	if(gpfout!=NULL)
		gpfout->printSet(gnprefix_len, gpprefix_itemset, nsupport);
}


