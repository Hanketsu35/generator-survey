#pragma once 

#include <stdio.h>
#include "Global.h"
#include "parameters.h"

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

extern FSout *gpfgout;
extern FSout *gpnbout;


inline void OutputOneGenerator(int nsupport)
{

	gdtotal_generators++;
	if(gnmax_pattern_len<gnprefix_len)
		gnmax_pattern_len = gnprefix_len;

	if(goparameters.bresult_name_given)
		gpfgout->printSet(gnprefix_len, gpprefix_itemset, nsupport);
}

inline void OutputOneGenerator(int nitem, int nsupport)
{

	gdtotal_generators++;
	if(gnmax_pattern_len<gnprefix_len+1)
		gnmax_pattern_len = gnprefix_len+1;

	if(goparameters.bresult_name_given)
	{
		gpprefix_itemset[gnprefix_len] = nitem;
		gpfgout->printSet(gnprefix_len+1, gpprefix_itemset, nsupport);
	}
}


inline void OutputOneNegPat(int nitem, int nsupport)
{
	gdnegborder_size++;
	if(nsupport==0)
		gdnum_of_zerosets++;
	gpprefix_itemset[gnprefix_len] = nitem;

	if(goparameters.bresult_name_given)
		gpnbout->printSet(gnprefix_len+1, gpprefix_itemset, nsupport);

}




