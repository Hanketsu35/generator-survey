#pragma once 


typedef struct FP_NODE
{
	int	frequency;
	int nitem_order;
	FP_NODE *pchild;
	FP_NODE	*prightsibling;
	FP_NODE *pparent;
	FP_NODE *pnode_link;
} FP_NODE;

typedef struct
{
	int nitem; 
	int nsupport;
	FP_NODE *pconddb;
	int order;
} HEADER_NODE;
typedef HEADER_NODE* HEADER_TABLE;



class FPtree
{
	void CountFreqItems(HEADER_TABLE pheader_table, int nitem_order, int *pitem_sup_map);
	FP_NODE* BuildNewFPTree(FP_NODE *pconddb, HEADER_TABLE pnewheader_table, int *pitem_order_map);

public:
	void InsertTransaction(FP_NODE* &proot, HEADER_TABLE pheader_table, int* ptransaction, int length, int frequency);
	
	void DepthFGGrowth(FP_NODE *proot, HEADER_TABLE pheader_table, int num_of_freqitems);

	bool IsSinglePath(FP_NODE *proot);

};

extern FPtree goFPtree;
extern HEADER_TABLE gpheader_table;

int comp_item_freq_des(const void *e1, const void *e2);
