#include <stdlib.h>
#include <stdio.h>

#include "ScanDBMine.h"
#include "data.h"
#include "inline_routine.h"

CScanDBMine  goDBMiner;

// Enumerate all the frequent items in the database
int CScanDBMine::ScanDBCountFreqItems(int* &pitem_sup_map)
{
	Transaction* ptransaction;
	int *ptemp_map, ncapacity, nnewcapacity;
	int i;

	ncapacity = ITEM_SUP_MAP_SIZE;
	pitem_sup_map = NewIntArray(ncapacity, 0);

	gndb_size = 0;
	gnmax_trans_len = 0;
	gnmax_item_id = 0;

	ptransaction=gpdata->getNextTransaction();
	while(ptransaction)
	{
		if(ptransaction->length>0)
		{
			gndb_size++;
			if(gnmax_trans_len<ptransaction->length)
				gnmax_trans_len = ptransaction->length;
			for(i=0;i<ptransaction->length;i++)
			{
				if(gnmax_item_id<ptransaction->t[i])
					gnmax_item_id = ptransaction->t[i];

				if(ptransaction->t[i]>=ncapacity)
				{
					nnewcapacity = MAX(2*ncapacity, ptransaction->t[i]+1);
					ptemp_map = NewIntArray(nnewcapacity);
					memcpy(ptemp_map, pitem_sup_map, sizeof(int)*ncapacity);
					memset(&(ptemp_map[ncapacity]), 0, sizeof(int)*(nnewcapacity-ncapacity));
					DelIntArray(pitem_sup_map, ncapacity);
					pitem_sup_map = ptemp_map;
					ncapacity = nnewcapacity;
				}
				pitem_sup_map[ptransaction->t[i]]++;
			}
		}
		ptransaction = gpdata->getNextTransaction();
	}

	gnmax_trans_len++;
	gnmax_item_id++;

	return ncapacity;

}


FP_NODE* CScanDBMine::ScanDBBuildFPtree(HEADER_TABLE pheader_table, int *pitem_order_map)
{
	Transaction *ptransaction;
	int ntrans_len, i, order;
	FP_NODE *proot;

	proot = NULL;
	ptransaction = gpdata->getNextTransaction();
	while(ptransaction)
	{
		if(ptransaction->length>0)
		{
			ntrans_len = 0;
			for(i=0;i<ptransaction->length;i++)
			{
				order = pitem_order_map[ptransaction->t[i]];
				if(order>=0)
				{
					gptransaction[ntrans_len] = order;
					ntrans_len++;
				}
			}

			if(ntrans_len>1)
			{
				//qsort((void*)gptransaction, ntrans_len, sizeof(int), comp_int_asc);
				sort_trans(gptransaction, ntrans_len);
				goFPtree.InsertTransaction(proot, pheader_table, gptransaction, ntrans_len, 1);
			}
		}
		ptransaction = gpdata->getNextTransaction();
	}

	return proot;
}

