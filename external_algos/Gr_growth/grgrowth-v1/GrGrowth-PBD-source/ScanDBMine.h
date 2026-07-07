#pragma once 

#include <stdio.h>
#include <stdlib.h>

#include "Global.h"	
#include "FPtree.h"

class CScanDBMine
{
public:
	int ScanDBCountFreqItems(int* &pitem_sup_map);
	FP_NODE* ScanDBBuildFPtree(HEADER_TABLE pheader_table, int *pitem_order_map);

};

extern CScanDBMine  goDBMiner;


