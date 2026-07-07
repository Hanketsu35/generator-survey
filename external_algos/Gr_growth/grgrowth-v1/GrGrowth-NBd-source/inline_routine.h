#pragma once 

#include <string.h>
#include "Global.h"
#include "parameters.h"

/*
// for detecting memory leak
#include <afx.h>
#define new DEBUG_NEW
#ifdef _DEBUG
#undef THIS_FILE
static char THIS_FILE[]=__FILE__;
#define new DEBUG_NEW
#endif
//*/


inline void IncMemSize(int size)
{
	gdused_mem_size += size;
	if(gdused_mem_size>gdmax_used_mem_size)
		gdmax_used_mem_size = gdused_mem_size;
}
inline void DecMemSize(int size)
{
	gdused_mem_size -= size;
}



//=============================================================================
inline int* NewIntArray(int length)
{
	IncMemSize(length*sizeof(int));
	return new int[length];
}
inline void DelIntArray(int* parray, int length)
{
	DecMemSize(length*sizeof(int));
	delete []parray;
}
inline int** NewIntPointerArray(int length)
{
	IncMemSize(length*sizeof(int*));
	return new int*[length];
}
inline void DelIntPointerArray(int** ppitemsets, int length)
{
	DecMemSize(length*sizeof(int*));
	delete []ppitemsets;
}
inline int* NewIntArray(int length, int value)
{
	int *parray;

	parray = NewIntArray(length);
	memset(parray, value, sizeof(int)*length);
	return parray;
}
inline char* NewCharArray(int length)
{
	IncMemSize(length*sizeof(char));
	return new char[length];
}
inline void DelCharArray(char* parray, int length)
{
	DecMemSize(length*sizeof(char));
	delete []parray;
}
inline unsigned short* NewUShortArray(int length)
{
	IncMemSize(length*sizeof(unsigned short));
	return new unsigned short[length];
}
inline void DelUShortArray(unsigned short* parray, int length)
{
	DecMemSize(length*sizeof(unsigned short));
	delete []parray;
}

//=============================================================================


//-----------------------------------------------------------------------------
#include "FPtree.h"

#define FPNODE_PAGE_SIZE (1<<10)

struct FPNODE_PAGE
{
	FP_NODE *pfpnodes;
	FPNODE_PAGE *pnext;
};
struct FPNODE_BUF
{
	FPNODE_PAGE *phead;
	FPNODE_PAGE *pcur_page; 
	int ncur_pos;
	int ntotal_pages;
};
extern FPNODE_BUF gofpnode_buf;

inline FPNODE_PAGE* NewFPNodePage()
{
	FPNODE_PAGE *pfppage;

	pfppage = new FPNODE_PAGE;
	IncMemSize(sizeof(FPNODE_PAGE));
	pfppage->pfpnodes = new FP_NODE[FPNODE_PAGE_SIZE];
	IncMemSize(sizeof(FP_NODE)*FPNODE_PAGE_SIZE);
	pfppage->pnext = NULL;

	return pfppage;
}
inline void DelFFNodePage(FPNODE_PAGE* pfppage)
{
	delete []pfppage->pfpnodes;
	DecMemSize(sizeof(FP_NODE)*FPNODE_PAGE_SIZE);
	delete pfppage;
	DecMemSize(sizeof(FPNODE_PAGE));
}

inline FP_NODE* NewOneFPNode()
{
	FP_NODE *pfpnode;
	FPNODE_PAGE *pnewfppage;

	if(gofpnode_buf.ncur_pos==FPNODE_PAGE_SIZE)
	{
		if(gofpnode_buf.pcur_page->pnext==NULL)
		{
			pnewfppage = NewFPNodePage();
			gofpnode_buf.pcur_page->pnext = pnewfppage;
			gofpnode_buf.pcur_page = pnewfppage;
			gofpnode_buf.ntotal_pages++;
		}
		else 
			gofpnode_buf.pcur_page = gofpnode_buf.pcur_page->pnext;
		gofpnode_buf.ncur_pos = 0;
	}
	
	pfpnode = &(gofpnode_buf.pcur_page->pfpnodes[gofpnode_buf.ncur_pos]);
	gofpnode_buf.ncur_pos++;
	
	return pfpnode;
}
//--------------------------------------------------------------------------



//=============================================================================
extern HEADER_TABLE gpdfs_header_array;
extern int gndfs_header_size;
extern int gndfs_header_pos;

inline HEADER_TABLE NewHeaderTable(int num_of_freqitems)
{
	HEADER_TABLE pheader_table;

	if(gndfs_header_pos+num_of_freqitems<=gndfs_header_size)
	{
		pheader_table = &(gpdfs_header_array[gndfs_header_pos]);
		gndfs_header_pos += num_of_freqitems;
	}
	else 
	{
		IncMemSize(num_of_freqitems*sizeof(HEADER_NODE));
		pheader_table = new HEADER_NODE[num_of_freqitems];
	}

	return pheader_table;
}

inline void DelHeaderTable(HEADER_TABLE pheader_table, int num_of_freqitems)
{
	if((uintptr_t)pheader_table>=(uintptr_t)gpdfs_header_array && (uintptr_t)pheader_table<(uintptr_t)gpdfs_header_array+sizeof(HEADER_NODE)*gndfs_header_size)
	{
		gndfs_header_pos -= num_of_freqitems;
	}
	else 
	{
		DecMemSize(num_of_freqitems*sizeof(HEADER_NODE));
		delete []pheader_table;
	}

}


//=============================================================================



//------------------------------------------------------------------------------
inline void Init()
{
	int length;

	length = MIN(gnmax_trans_len, gntotal_freqitems);
	gptransaction = NewIntArray(length);
	gpsort_trans_buf = NewCharArray(gntotal_freqitems);
	memset(gpsort_trans_buf, 0, sizeof(char)*gntotal_freqitems);
	gpitem_bitmap = NewCharArray(gnmax_item_id);
	memset(gpitem_bitmap, 0, sizeof(char)*gnmax_item_id);
	gpcfp_itemset = NewIntArray(length);


	//for dfs mining
	gndfs_header_size = gntotal_freqitems*3;
	gpdfs_header_array = new HEADER_NODE[gndfs_header_size];
	IncMemSize(sizeof(HEADER_NODE)*gndfs_header_size);
	gndfs_header_pos = 0;


    // for allocating space for fptree
	gofpnode_buf.phead = NewFPNodePage();
	gofpnode_buf.pcur_page = gofpnode_buf.phead;
	gofpnode_buf.ncur_pos = 0;
	gofpnode_buf.ntotal_pages = 1;	
}

inline void Reset(FPNODE_PAGE *pcur_page, int ncur_pos)
{
	gofpnode_buf.pcur_page = pcur_page;
	gofpnode_buf.ncur_pos = ncur_pos;
}

inline void Destroy()
{
	int length;

	length = MIN(gnmax_trans_len, gntotal_freqitems);
	DelIntArray(gptransaction, length);
	DelCharArray(gpsort_trans_buf, gntotal_freqitems);
	DelCharArray(gpitem_bitmap, gnmax_item_id);
	DelIntArray(gpcfp_itemset, length);

	//for DFS mining
	DecMemSize(sizeof(HEADER_NODE)*gndfs_header_size);
	delete []gpdfs_header_array;

	//releasing fpnode buffer
	FPNODE_PAGE *pfppage, *pnext_fppage;
	pfppage = gofpnode_buf.phead;
	while(pfppage!=NULL)
	{
		pnext_fppage = pfppage->pnext;
		DelFFNodePage(pfppage);
		pfppage = pnext_fppage;	
		gofpnode_buf.ntotal_pages--;
	}
	if(gofpnode_buf.ntotal_pages!=0)
		printf("Error with number of FPNode pages\n");
}

//------------------------------------------------------------------------------


//------------------------------------------------------------------------------
#include "PatternSet.h"

inline PAT_PAGE* NewPatPage()
{
	IncMemSize(sizeof(PAT_PAGE));

	PAT_PAGE *ppat_page;
	ppat_page = new PAT_PAGE;
	ppat_page->pnext = NULL;
	return ppat_page;
}
inline void DelPatPage(PAT_PAGE *ppat_page)
{
	DecMemSize(sizeof(PAT_PAGE));
	delete ppat_page;
}

inline PAT_MAP* NewPatMap(int nstart)
{
	IncMemSize(sizeof(PAT_MAP));

	PAT_MAP *ppat_map;
	ppat_map = new PAT_MAP;
	ppat_map->nstart = nstart;
	ppat_map->num_of_nodes = 0;
	for(int i=0;i<MAP_SIZE;i++)
		ppat_map->ppat_map_nodes[i] = NULL;

	return ppat_map;
}
inline void DelPatMap(PAT_MAP* ppat_map)
{
	DecMemSize(sizeof(PAT_MAP));
	delete ppat_map;
}

inline MAP_NODE_PAGE* NewMapNodePage()
{
	MAP_NODE_PAGE *pmapnode_page;

	IncMemSize(sizeof(MAP_NODE_PAGE));
	pmapnode_page = new MAP_NODE_PAGE;
	pmapnode_page->pnext = NULL;
	return pmapnode_page;
}
inline void DelMapNodePage(MAP_NODE_PAGE* pmapnode_page)
{
	DecMemSize(sizeof(MAP_NODE_PAGE));
	delete pmapnode_page;
}
inline SUBSET_NODE* NewSubsetNodeArray(int length)
{
	IncMemSize(sizeof(SUBSET_NODE)*length);
	return new SUBSET_NODE[length];
}
inline void DelSubsetNodeArray(SUBSET_NODE* pnodearray, int length)
{
	DecMemSize(sizeof(SUBSET_NODE)*length);
	delete []pnodearray;
}
//------------------------------------------------------------------------------



inline void sort_trans(int *ptransaction, int ntrans_len)
{
	int i, j;

	if(gnum_of_newfreqitems/ntrans_len>64)
		qsort(ptransaction, ntrans_len, sizeof(int), comp_int_asc);
	else
	{
		for(i=0;i<ntrans_len;i++)
			gpsort_trans_buf[ptransaction[i]] = 1;

		j = 0;
		for(i=0;i<gnum_of_newfreqitems;i++)
		{
			if(gpsort_trans_buf[i])
			{
				ptransaction[j] = i;
				j++;
				gpsort_trans_buf[i] = 0;
			}
		}
	}

}
