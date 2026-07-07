#pragma once 

#include <stdio.h>
#include "FPtree.h"

#define ITEM_HASH_BITMAP  0x001f
#define MAP_SIZE 1299709
//#define MAP_SIZE 1372549
//#define MAP_SIZE 2135957

#define MAX_MAP_NODE_NUM  MAP_SIZE

#define PAT_PAGE_SIZE (1<<15)
#define MAP_NODE_PAGE_SIZE (1<<15)

struct PAT_PAGE
{
	unsigned short ppatterns[PAT_PAGE_SIZE];
	PAT_PAGE *pnext;
};

struct PAT_SET
{
	PAT_PAGE *phead;
	PAT_PAGE *ptail;
	int ncur_pos;
};

struct PAT_MAP_NODE
{
	unsigned short *ppattern;
	PAT_MAP_NODE *pnext;
};
struct MAP_NODE_PAGE
{
	PAT_MAP_NODE pmapnodes[MAP_NODE_PAGE_SIZE];
	MAP_NODE_PAGE *pnext;
}; 
struct MAP_NODE_BUF
{
	MAP_NODE_PAGE *phead;
	MAP_NODE_PAGE *ptail;
	int ncur_pos;
}; 

struct PAT_MAP
{
	int nstart;
	int num_of_nodes; 
	PAT_MAP_NODE *ppat_map_nodes[MAP_SIZE];
	PAT_MAP *pprev;
}; 

struct SUBSET_NODE
{
	int nsupport;
	int nsubset_sum;
	int flag;
}; 
#define DEFAULT_SET_LEN   15

class PatternSet
{
	PAT_SET mopatternset;
	MAP_NODE_BUF momap_node_buf;
	PAT_MAP *mppat_map;

	SUBSET_NODE* mpsubset_nodes;
	int mnset_len;

public:

	void Init();

	void Insert(int nitem, int nsupport);
	void Insert(int nsupport);

	bool IsGenerator(int nitem, int nsupport);
	bool IsMinimal(int nitem);
	
	bool IskFree(int nitem, int nsupport, int nsubsup1, int nsubsup2);
	int search_one_set(unsigned int nmap_value, bool biscurmap, int length);
	int calc_subset_sum(int k, int nbaseset_sup, int nbaseset_pos);

	void CheckMap(int nitem_order);
	void Destroy();

	void GetMapStatis();
	void PrintMapStatis(FILE* fp_sum);
};

extern PatternSet gopatternset;
extern int *gpitem_order_map;
extern unsigned int gnmap_value;
extern unsigned short *gpprefix_orderset;
extern int *gpexcludestack;
extern int *gpenum_stack;

extern int gnmax_search_depth;
extern double gdavg_search_depth;
extern int gnsearch_times;


inline unsigned int HashAdd1Item(unsigned int nmap_value, int nitem)
{
	return (unsigned int)(nmap_value+(1<<(gpitem_order_map[nitem]&ITEM_HASH_BITMAP))+gpitem_order_map[nitem]+(1<<(nitem&ITEM_HASH_BITMAP))+nitem+1);
}

inline unsigned int HashRemove1Item(unsigned int nmap_value, int nitem)
{
	return (unsigned int)(nmap_value-(1<<(gpitem_order_map[nitem]&ITEM_HASH_BITMAP))-gpitem_order_map[nitem]-(1<<(nitem&ITEM_HASH_BITMAP))-nitem-1);
}

inline unsigned int HashFunc(unsigned int nmap_value)
{
	return nmap_value%MAP_SIZE;
}

inline unsigned int HashItemset(unsigned short *pitemset, int length)
{
	unsigned int nmap_value;
	int i;

	nmap_value = 0;
	for(i=0;i<length;i++)
		nmap_value = HashAdd1Item(nmap_value, gpheader_table[pitemset[i]].nitem);

	return nmap_value;
}
