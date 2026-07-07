#include <stdlib.h>
#include <stdio.h>


#include "FPtree.h"
#include "inline_routine.h"


FPtree goFPtree;


void FPtree::InsertTransaction(FP_NODE* &proot, HEADER_TABLE pheader_table, int* ptransaction, int length, int frequency)
{
	FP_NODE *pcur_node, *pnew_node, *pparent, *pleftsib;
	int i, j;

	pcur_node = proot;
	pparent = NULL;
	pleftsib = NULL;
	for(i=0;i<length;i++)
	{
		while(pcur_node!=NULL && pcur_node->nitem_order<ptransaction[i])
		{
			pleftsib = pcur_node;
			pcur_node = pcur_node->prightsibling;
		}

		if(pcur_node==NULL || pcur_node->nitem_order>ptransaction[i])
		{
			pnew_node = NewOneFPNode();
			pnew_node->nitem_order = ptransaction[i];
			pnew_node->frequency = frequency;
			pnew_node->pchild = NULL;
			pnew_node->pparent = pparent;
			pnew_node->prightsibling = pcur_node;
			if(pleftsib!=NULL)
				pleftsib->prightsibling = pnew_node;
			else if(pparent!=NULL)
				pparent->pchild = pnew_node;
			pnew_node->pnode_link = pheader_table[pnew_node->nitem_order].pconddb;
			pheader_table[pnew_node->nitem_order].pconddb = pnew_node;
			if(i==0 && pleftsib==NULL)
				proot = pnew_node;
			pparent = pnew_node;
			for(j=i+1;j<length;j++)
			{
				pnew_node = NewOneFPNode();
				pnew_node->nitem_order = ptransaction[j];
				pnew_node->frequency = frequency;
				pnew_node->pchild = NULL;
				pnew_node->pparent = pparent;
				pparent->pchild = pnew_node;
				pnew_node->prightsibling = NULL;
				pnew_node->pnode_link = pheader_table[pnew_node->nitem_order].pconddb;
				pheader_table[pnew_node->nitem_order].pconddb = pnew_node;
				pparent = pnew_node;
			}
			break;
		}
		else 
		{
			pcur_node->frequency += frequency;
			pparent = pcur_node;
			pcur_node = pcur_node->pchild;
			pleftsib = NULL;
		}
	}
}

void FPtree::CountFreqItems(HEADER_TABLE pheader_table, int nitem_order, int *pitem_sup_map)
{
	FP_NODE *pitemnode, *pfpnode;
	int ncount;

	pitemnode = pheader_table[nitem_order].pconddb;
	while(pitemnode!=NULL)
	{
		ncount = pitemnode->frequency;
		pfpnode = pitemnode->pparent;
		while(pfpnode!=NULL)
		{
			pitem_sup_map[pfpnode->nitem_order] += ncount;
			pfpnode = pfpnode->pparent;
		}
		pitemnode = pitemnode->pnode_link;
	}
}


FP_NODE* FPtree::BuildNewFPTree(FP_NODE *pconddb, HEADER_TABLE pnewheader_table, int *pitem_order_map)
{
	FP_NODE *pnewroot, *pitemnode, *pfpnode;
	int ncount, ntrans_len;

	pnewroot = NULL;

	pitemnode = pconddb;
	while(pitemnode!=NULL)
	{
		ncount = pitemnode->frequency;
		pfpnode = pitemnode->pparent;
		ntrans_len = 0;
		while(pfpnode!=NULL)
		{
			if(pitem_order_map[pfpnode->nitem_order]>=0)
			{
				gptransaction[ntrans_len] = pitem_order_map[pfpnode->nitem_order];
				ntrans_len++;
			}
			pfpnode = pfpnode->pparent;
		}
		if(ntrans_len>1)
		{
			sort_trans(gptransaction, ntrans_len);
			InsertTransaction(pnewroot, pnewheader_table, gptransaction, ntrans_len, ncount);
		}
		pitemnode = pitemnode->pnode_link;
	}

	return pnewroot;
}


bool FPtree::IsSinglePath(FP_NODE *proot)
{
	FP_NODE *pfpnode;
	
	pfpnode = proot;
	while(pfpnode!=NULL && pfpnode->prightsibling==NULL)
		pfpnode = pfpnode->pchild;
	if(pfpnode==NULL)
		return true;
	else 
		return false;
}

//sort items in descending frequency order
int comp_item_freq_des(const void *e1, const void *e2)
{
	HEADER_NODE *p1, *p2;
	p1 = (HEADER_NODE *) e1;
	p2 = (HEADER_NODE *) e2;

	if ((p1->nsupport>p2->nsupport) )
		return -1;
	else if (p1->nsupport<p2->nsupport)
		return 1;
	else 
		return 0;
}

