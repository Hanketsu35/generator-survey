#include <stdlib.h>

#include "PatternSet.h"
#include "Global.h"
#include "inline_routine.h"
#include "fsout.h"

PatternSet gopatternset;
int *gpitem_order_map;
unsigned int gnmap_value;
unsigned short *gpprefix_orderset;

int gnmax_search_depth;
double gdavg_search_depth;
int gnsearch_times;
int *gpexcludestack;
int *gpenum_stack;

void PatternSet::Init()
{
	mopatternset.phead = NewPatPage();
	mopatternset.ptail = mopatternset.phead;
	mopatternset.ncur_pos = 0;

	mppat_map = NewPatMap(0);
	mppat_map->pprev = NULL;

	momap_node_buf.phead = NewMapNodePage();
	momap_node_buf.ptail = momap_node_buf.phead;
	momap_node_buf.ncur_pos = 0;

	if(goparameters.k>1)
	{
		mnset_len = DEFAULT_SET_LEN;
		mpsubset_nodes = NewSubsetNodeArray((1<<mnset_len));
		memset(mpsubset_nodes, 0, sizeof(SUBSET_NODE)*(1<<mnset_len));
		gpexcludestack = NewIntArray(gnmax_trans_len);
		gpenum_stack = NewIntArray(gnmax_trans_len);
	}
	
	gnmax_search_depth = 0;
	gdavg_search_depth = 0;
	gnsearch_times = 0;
}

void PatternSet::Insert(int nitem, int nsupport)
{
	gpprefix_itemset[gnprefix_len] = nitem;
	gpprefix_orderset[gnprefix_len] = gpitem_order_map[nitem];
	gnprefix_len++;
	gnmap_value = HashAdd1Item(gnmap_value, nitem);

	Insert(nsupport);
	
	gnmap_value = HashRemove1Item(gnmap_value, nitem);
	gnprefix_len--;
}

void PatternSet::Insert(int nsupport)
{
	if(gnprefix_len==1)
		return; 

	unsigned int nvalue; 
	PAT_MAP_NODE* pmap_node;

//	OutputOneGenerator(nsupport);	
	nvalue = HashFunc(gnmap_value);

	//inserting a map node
	if(momap_node_buf.ncur_pos==MAP_NODE_PAGE_SIZE)
	{
		MAP_NODE_PAGE* pmap_node_page;

		pmap_node_page = NewMapNodePage();
		pmap_node_page->pnext = NULL;
		momap_node_buf.ptail->pnext = pmap_node_page;
		momap_node_buf.ptail = pmap_node_page;
		momap_node_buf.ncur_pos = 0;
	}
	pmap_node = &(momap_node_buf.ptail->pmapnodes[momap_node_buf.ncur_pos]);
	momap_node_buf.ncur_pos++;
	pmap_node->pnext = mppat_map->ppat_map_nodes[nvalue];
	mppat_map->ppat_map_nodes[nvalue] = pmap_node;
	mppat_map->num_of_nodes++;

	//inserting the pattern 
	if(mopatternset.ncur_pos+gnprefix_len+5>=PAT_PAGE_SIZE)
	{
		PAT_PAGE *ppat_page;

		//memset(&(mopatternset.ptail->ppatterns[mopatternset.ncur_pos]), -1, sizeof(unsigned short)*(PAT_PAGE_SIZE-mopatternset.ncur_pos));
		ppat_page = NewPatPage();
		ppat_page->pnext = NULL;
		mopatternset.ptail->pnext = ppat_page;
		mopatternset.ptail = ppat_page;
		mopatternset.ncur_pos = 0;
	}
	pmap_node->ppattern = &(mopatternset.ptail->ppatterns[mopatternset.ncur_pos]);
	mopatternset.ptail->ppatterns[mopatternset.ncur_pos] = gnprefix_len;
	mopatternset.ncur_pos++;
	memcpy(&(mopatternset.ptail->ppatterns[mopatternset.ncur_pos]), &nsupport, sizeof(int));
	mopatternset.ncur_pos += 2;
	memcpy(&(mopatternset.ptail->ppatterns[mopatternset.ncur_pos]), gpprefix_orderset, gnprefix_len*sizeof(unsigned short));
	mopatternset.ncur_pos += gnprefix_len;
	memcpy(&(mopatternset.ptail->ppatterns[mopatternset.ncur_pos]), &gnmap_value, sizeof(unsigned int));
	mopatternset.ncur_pos += 2;
}

int PatternSet::IsGenerator(int nitem, int nsupport)
{
	PAT_MAP_NODE *pmap_node;
	int length, i, j, nsubset_sup, nsubset_len;
	unsigned short *psubset;
	unsigned int nvalue, nsubset_map_value, nsubset_hash_value, npat_map_value;
	bool bfound, bisgenerator;
//	int nsearch_depth;

	nvalue = HashAdd1Item(gnmap_value, nitem);
	length = gnprefix_len+1;
	if(length<3)
		printf("Error with generator length\n");

	bisgenerator = true;
	for(i=length-3;i>=0;i--)
	{
		gpitem_bitmap[gpprefix_orderset[i]] = 0;

		nsubset_map_value = HashRemove1Item(nvalue, gpprefix_itemset[i]);
		nsubset_hash_value = HashFunc(nsubset_map_value);
		if(i==0)
		{
			PAT_MAP *ppat_map;
			int nmax_order;

			nmax_order = gpitem_order_map[nitem];
			ppat_map = mppat_map;
			if(ppat_map->nstart>nmax_order)
			{
				for(j=1;j<gnprefix_len && ppat_map->nstart>nmax_order;j++)
				{
					if(nmax_order<gpprefix_orderset[j])
						nmax_order = gpprefix_orderset[j];
				}
				while(ppat_map->nstart>nmax_order)
					ppat_map = ppat_map->pprev;
			}
			pmap_node = ppat_map->ppat_map_nodes[nsubset_hash_value];
		}
		else
			pmap_node = mppat_map->ppat_map_nodes[nsubset_hash_value];
		bfound = false;
		if(pmap_node!=NULL)
		{
//			nsearch_depth = 0;
			while(pmap_node!=NULL)
			{
//				nsearch_depth++;
				nsubset_len = pmap_node->ppattern[0];
				if(nsubset_len==gnprefix_len)
				{
					memcpy(&nsubset_sup, &(pmap_node->ppattern[1]), sizeof(int));
					if(nsubset_sup>=nsupport)
					{
						memcpy(&npat_map_value, &(pmap_node->ppattern[3+nsubset_len]), sizeof(unsigned int));
						if(npat_map_value==nsubset_map_value)
						{
							psubset = &(pmap_node->ppattern[3]);
							for(j=0;j<nsubset_len && gpitem_bitmap[psubset[j]];j++);
							if(j==nsubset_len)
							{
								bfound = true; 
								if(nsubset_sup==nsupport)
								{
									bisgenerator = false;
									gnrdnt_item = gpprefix_itemset[i];
								}
								break;
							}
						}
					}
				}
				pmap_node = pmap_node->pnext;
			}
//			if(gnmax_search_depth<nsearch_depth)
//				gnmax_search_depth=nsearch_depth;
//			gdavg_search_depth += nsearch_depth;
//			gnsearch_times++;
		}
		gpitem_bitmap[gpprefix_orderset[i]] = 1;
		if(!bfound)
			return 0;
	}
	if(bisgenerator)	
		return IS_GENERATOR;
	else
		return IS_FREQBORDER;
}


bool PatternSet::IsMinimal(int nitem)
{
	PAT_MAP_NODE *pmap_node;
	int length, i, j, nsubset_len;
	unsigned short *psubset;
	unsigned int nvalue, nsubset_map_value, nsubset_hash_value, npat_map_value;
	bool bfound;
//	int nsearch_depth;

	nvalue = HashAdd1Item(gnmap_value, nitem);
	length = gnprefix_len+1;
	if(length<3)
		printf("Error with negative itemset length\n");

	for(i=length-3;i>=0;i--)
	{
		gpitem_bitmap[gpprefix_orderset[i]] = 0;

		nsubset_map_value = HashRemove1Item(nvalue, gpprefix_itemset[i]);
		nsubset_hash_value = HashFunc(nsubset_map_value);
		if(i==0)
		{
			PAT_MAP *ppat_map;
			int nmax_order;

			nmax_order = gpitem_order_map[nitem];
			ppat_map = mppat_map;
			if(ppat_map->nstart>nmax_order)
			{
				for(j=1;j<gnprefix_len && ppat_map->nstart>nmax_order;j++)
				{
					if(nmax_order<gpprefix_orderset[j])
						nmax_order = gpprefix_orderset[j];
				}
				while(ppat_map->nstart>nmax_order)
					ppat_map = ppat_map->pprev;
			}
			pmap_node = ppat_map->ppat_map_nodes[nsubset_hash_value];
		}
		else
			pmap_node = mppat_map->ppat_map_nodes[nsubset_hash_value];
		bfound = false;
		if(pmap_node!=NULL)
		{
//			nsearch_depth = 0;
			while(pmap_node!=NULL)
			{
//				nsearch_depth++;
				nsubset_len = pmap_node->ppattern[0];
				if(nsubset_len==gnprefix_len)
				{
					memcpy(&npat_map_value, &(pmap_node->ppattern[3+nsubset_len]), sizeof(unsigned int));
					if(npat_map_value==nsubset_map_value)
					{
						psubset = &(pmap_node->ppattern[3]);
						for(j=0;j<nsubset_len && gpitem_bitmap[psubset[j]];j++);
						if(j==nsubset_len)
						{
							bfound = true; 
							break;
						}
					}
				}
				pmap_node = pmap_node->pnext;
			}
//			if(gnmax_search_depth<nsearch_depth)
//				gnmax_search_depth=nsearch_depth;
//			gdavg_search_depth += nsearch_depth;
//			gnsearch_times++;
		}
		gpitem_bitmap[gpprefix_orderset[i]] = 1;
		if(!bfound)
			return false;
	}
	return true;
}

int PatternSet::IskFree(int nitem, int nsupport, int nsubsup1, int nsubsup2)
{
	int k, i, j, top;
	unsigned int nvalue, nsubset_map_value;
	int length, nsubset_sup, nsubset_len, nsubset_pos, nsubset_sum, norder;
	bool bisgenerator;

	nvalue = HashAdd1Item(gnmap_value, nitem);
	length = gnprefix_len+1;

	//----------------------------------
	if(length==2)
	{
		if(nsubsup1+nsubsup2==nsupport+gndb_size)
			return IS_FREQBORDER;
		else
			return IS_GENERATOR;
	}
	//-----------------------------------
	
	if(length>mnset_len)
	{
		SUBSET_NODE* ptempnodes;

		ptempnodes = NewSubsetNodeArray((1<<length));
		DelSubsetNodeArray(mpsubset_nodes, (1<<mnset_len));
		mpsubset_nodes = ptempnodes;
		mnset_len = length;
	}
	memset(mpsubset_nodes, 0, sizeof(SUBSET_NODE)*(1<<length));

	bisgenerator = true;
	//=======================================================
	nsubset_pos = (1<<length)-1-(1<<(length-1));
	mpsubset_nodes[nsubset_pos].nsupport = nsubsup1;
	mpsubset_nodes[nsubset_pos].nsubset_sum = nsubsup1;
	mpsubset_nodes[nsubset_pos].flag = 1;
	nsubset_pos += (1<<(length-2));
	mpsubset_nodes[nsubset_pos].nsupport = nsubsup2;
	mpsubset_nodes[nsubset_pos].nsubset_sum = nsubsup2;
	mpsubset_nodes[nsubset_pos].flag = 1;
	for(i=length-3;i>=0;i--)
	{
		gpitem_bitmap[gpprefix_orderset[i]] = 0;

		nsubset_map_value = HashRemove1Item(nvalue, gpprefix_itemset[i]);
		if(i==0)
			nsubset_sup = search_one_set(nsubset_map_value, false, length-1);
		else
			nsubset_sup = search_one_set(nsubset_map_value, true, length-1);
		gpitem_bitmap[gpprefix_orderset[i]] = 1;
		if(nsubset_sup==-1)
			return 0;
		else if(nsubset_sup==nsupport)
			bisgenerator = false;
		else if(bisgenerator)
		{
			nsubset_pos += (1<<i);
			mpsubset_nodes[nsubset_pos].nsupport = nsubset_sup;
			mpsubset_nodes[nsubset_pos].nsubset_sum = nsubset_sup;
			mpsubset_nodes[nsubset_pos].flag = 1;
		}
	}
	if(!bisgenerator)
		return IS_FREQBORDER;
	//===============================================

	//-----------------------------------------
	for(k=2;k<=goparameters.k && k<length && bisgenerator;k++)
	{
		nsubset_pos = (1<<length)-1;
		nsubset_map_value = nvalue;
		nsubset_len = length-k;
		
		top = 0;
		for(j=length-1;j>=length-k;j--)
		{
			gpexcludestack[top] = j;
			top++;
			nsubset_pos -= (1<<j);
			nsubset_map_value = HashRemove1Item(nsubset_map_value, gpprefix_itemset[j]);
			gpitem_bitmap[gpprefix_orderset[j]] = 0;
		}
		if(nsubset_len==1)
			norder = 0;

		while(top==k)
		{
			if(nsubset_len==1)
			{
				if(nsubset_pos!=(1<<norder))
					printf("Error with subset position\n");
				nsubset_sup = gpheader_table[gpprefix_orderset[norder]].nsupport;
				norder++;
			}
			else if(gpitem_bitmap[gpprefix_orderset[0]])
				nsubset_sup = search_one_set(nsubset_map_value, true, nsubset_len);
			else 
				nsubset_sup = search_one_set(nsubset_map_value, false, nsubset_len);
			if(nsubset_sup<gnmin_sup)
				printf("Error with subset searching: Length:%d, Support:%d\n", length, nsubset_sup);
			nsubset_sum = calc_subset_sum(k, nsubset_sup, nsubset_pos);
			if(nsubset_sum==nsupport)
			{
				bisgenerator = false;
				break;
			}
			else 
			{
				mpsubset_nodes[nsubset_pos].nsupport = nsubset_sup;
				mpsubset_nodes[nsubset_pos].nsubset_sum = nsubset_sum;
				mpsubset_nodes[nsubset_pos].flag = 1;
			}

			top--;
			nsubset_pos += (1<<gpexcludestack[top]);
			nsubset_map_value = HashAdd1Item(nsubset_map_value, gpprefix_itemset[gpexcludestack[top]]);
			gpitem_bitmap[gpprefix_orderset[gpexcludestack[top]]] = 1;

			while(top>0 && gpexcludestack[top]==k-top-1)
			{
				top--;
				nsubset_pos += (1<<gpexcludestack[top]);
				nsubset_map_value = HashAdd1Item(nsubset_map_value, gpprefix_itemset[gpexcludestack[top]]);
				gpitem_bitmap[gpprefix_orderset[gpexcludestack[top]]] = 1;

			}
			if(top==0 && gpexcludestack[0]==k-1)
				break;
			if(top>=0)
			{
				gpexcludestack[top]--;
				nsubset_pos -= (1<<gpexcludestack[top]);
				nsubset_map_value = HashRemove1Item(nsubset_map_value, gpprefix_itemset[gpexcludestack[top]]);
				gpitem_bitmap[gpprefix_orderset[gpexcludestack[top]]] = 0;
				top++;
				while(top<k && gpexcludestack[top-1]>0)
				{
					gpexcludestack[top] = gpexcludestack[top-1]-1;
					nsubset_pos -= (1<<gpexcludestack[top]);
					nsubset_map_value = HashRemove1Item(nsubset_map_value, gpprefix_itemset[gpexcludestack[top]]);
					gpitem_bitmap[gpprefix_orderset[gpexcludestack[top]]] = 0;
					top++;
				}
			}
		}
		if(top==k)
		{
			for(j=0;j<k;j++)
				gpitem_bitmap[gpprefix_orderset[gpexcludestack[j]]] = 1;
		}
//		else if(top!=0)
//			printf("Error with the value of top\n");
//		for(j=0;j<length;j++)
//		{
//			if(gpitem_bitmap[gpprefix_orderset[j]]!=1)
//				printf("Error with bitmap\n");
//		}
	}
	//-----------------------------------------------------------------

	//=======================================================
	if(bisgenerator && goparameters.k>=length)
	{
		top = 0;
		for(j=length-1;j>=0;j--)
		{
			gpexcludestack[top] = j;
			top++;
		}
		nsubset_sum = calc_subset_sum(length, gndb_size, 0);
		if(nsubset_sum==nsupport)
			bisgenerator = false;
	}
	//=======================================================

	if(bisgenerator)
		return IS_GENERATOR;
	else 
		return IS_FREQBORDER;

}

int PatternSet::calc_subset_sum(int k, int nbaseset_sup, int nbaseset_pos)
{
	int nsum, nsign, nset_pos;
	int top;

	if(k==2)
	{
		nsum = -nbaseset_sup;
		nset_pos = nbaseset_pos+(1<<gpexcludestack[0]);
		if(mpsubset_nodes[nset_pos].flag==0)
			printf("Error with subset node flag\n");
		nsum += mpsubset_nodes[nset_pos].nsupport;
		nset_pos = nbaseset_pos+(1<<gpexcludestack[1]);
		if(mpsubset_nodes[nset_pos].flag==0)
			printf("Error with subset node flag\n");
		nsum += mpsubset_nodes[nset_pos].nsupport;

		return nsum;
	}

	if(k%2==0)
		nsign = -1;
	else 
		nsign = 1;
	nsum = nsign*nbaseset_sup;

	nset_pos = nbaseset_pos;
	nset_pos += (1<<gpexcludestack[0]);
	if(mpsubset_nodes[nset_pos].flag==0)
		printf("Error with subset node flag\n");
	nsum += mpsubset_nodes[nset_pos].nsubset_sum;

	nset_pos = nbaseset_pos;
	top = 0;
	gpenum_stack[top] = 1;
	top++;
	while(top>0)
	{
		nsign *= (-1);
		nset_pos += (1<<gpexcludestack[gpenum_stack[top-1]]);
		if(mpsubset_nodes[nset_pos].flag==0)
			printf("Error with subset node flag\n");
		nsum += nsign*mpsubset_nodes[nset_pos].nsupport;
		if(gpenum_stack[top-1]>=k-1)
		{
			nset_pos -= (1<<gpexcludestack[gpenum_stack[top-1]]);
			top--;
			if(top==0)
				break;
			else
			{
				nset_pos -= (1<<gpexcludestack[gpenum_stack[top-1]]);
				gpenum_stack[top-1]++;
			}
		}
		else 
		{
			gpenum_stack[top] = gpenum_stack[top-1]+1;
			top++;
		}
	}
	return nsum;
}

int PatternSet::search_one_set(unsigned int nmap_value, bool biscurmap, int length)
{
	PAT_MAP_NODE *pmap_node;
	int j;
	unsigned int nhash_value, npat_map_value;
	int npat_len, npat_sup;
	unsigned short* pgenerator;
//	int nsearch_depth;

/*
	int num_of_items;
	unsigned int ntest_map_value;
	if(gpitem_bitmap[gpprefix_orderset[0]]==1 && !biscurmap)
		printf("Error with biscurmap\n");
	else if(gpitem_bitmap[gpprefix_orderset[0]]==0 && biscurmap)
		printf("Error with biscurmap\n");

	num_of_items = 0;
	ntest_map_value = 0;
	for(j=0;j<gnprefix_len+1;j++)
	{
		if(gpitem_bitmap[gpprefix_orderset[j]])
		{
			num_of_items++;
			ntest_map_value = HashAdd1Item(ntest_map_value, gpprefix_itemset[j]);
		}
	}
	if(num_of_items!=length)
		printf("Error with subset length: %d %d\n", num_of_items, length);
	if(ntest_map_value!=nmap_value)
		printf("Error with subset map value: %d %d\n", ntest_map_value, nmap_value);
*/

	nhash_value = HashFunc(nmap_value);
	npat_sup = -1;

	if(!biscurmap)
	{
		PAT_MAP *ppat_map;
		int nmax_order;

		nmax_order = 0;
		ppat_map = mppat_map;
		if(ppat_map->nstart>nmax_order)
		{
			for(j=1;j<gnprefix_len+1 && ppat_map->nstart>nmax_order;j++)
			{
				if(gpitem_bitmap[gpprefix_orderset[j]] && nmax_order<gpprefix_orderset[j])
					nmax_order = gpprefix_orderset[j];
			}
			while(ppat_map->nstart>nmax_order)
				ppat_map = ppat_map->pprev;
		}
		pmap_node = ppat_map->ppat_map_nodes[nhash_value];
	}
	else
		pmap_node = mppat_map->ppat_map_nodes[nhash_value];
	if(pmap_node!=NULL)
	{
//		nsearch_depth = 0;
		while(pmap_node!=NULL)
		{
//			nsearch_depth++;
			npat_len = pmap_node->ppattern[0];
			if(npat_len==length)
			{
				memcpy(&npat_map_value, &(pmap_node->ppattern[3+npat_len]), sizeof(unsigned int));
				if(npat_map_value==nmap_value)
				{
					pgenerator = &(pmap_node->ppattern[3]);
					for(j=0;j<npat_len && gpitem_bitmap[pgenerator[j]];j++);
					if(j==npat_len)
					{
						memcpy(&npat_sup, &(pmap_node->ppattern[1]), sizeof(int));
						break;
					}
				}
			}
			pmap_node = pmap_node->pnext;
		}
//		if(gnmax_search_depth<nsearch_depth)
//			gnmax_search_depth=nsearch_depth;
//		gdavg_search_depth += nsearch_depth;
//		gnsearch_times++;
	}

	return npat_sup;
}

void PatternSet::CheckMap(int nitem_order)
{
	if(mppat_map->num_of_nodes<MAX_MAP_NODE_NUM)
		return;

	PAT_MAP* ppat_map;
	ppat_map = NewPatMap(nitem_order);
	ppat_map->pprev = mppat_map;
	mppat_map = ppat_map;

}

void PatternSet::Destroy()
{
	PAT_PAGE* ppat_page; 
	MAP_NODE_PAGE* pmap_node_page;
	PAT_MAP *ppat_map;

//	GetMapStatis();

	if(goparameters.k>1)
	{
		DelSubsetNodeArray(mpsubset_nodes, (1<<mnset_len));
		DelIntArray(gpexcludestack, gnmax_trans_len);
		DelIntArray(gpenum_stack, gnmax_trans_len);
	}

	ppat_page = mopatternset.phead;
	while(ppat_page!=NULL)
	{
		mopatternset.phead = ppat_page->pnext;
		DelPatPage(ppat_page);
		ppat_page = mopatternset.phead;
	}

	pmap_node_page = momap_node_buf.phead;
	while(pmap_node_page!=NULL)
	{
		momap_node_buf.phead = pmap_node_page->pnext;
		DelMapNodePage(pmap_node_page);
		pmap_node_page = momap_node_buf.phead;
	}

	ppat_map = mppat_map;
	while(ppat_map!=NULL)
	{
		mppat_map = ppat_map->pprev;
		DelPatMap(ppat_map);
		ppat_map = mppat_map;
	}
}

void PatternSet::PrintMapStatis(FILE* fp_sum)
{
	gdavg_search_depth /= gnsearch_times;

	fprintf(fp_sum, "%d  %d %.2f %d %d\t", MAP_SIZE, gnmax_search_depth, gdavg_search_depth, gnsearch_times, ITEM_HASH_BITMAP);
}

void PatternSet::GetMapStatis()
{
	FILE *fp_stat, *fp_long;
	PAT_MAP *ppat_map;
	PAT_MAP_NODE *pmap_node;
	int num_of_maps, nmax_map_size, nlocal_nonempty_entries, nmax_nonempty_entries, nlocal_max_map_depth, nmax_map_depth;
	double davg_map_size, davg_nonempty_entries, dlocal_avg_map_depth, davg_map_depth; 
	int i, ndepth;
	unsigned int nmap_value, nhash_value;
	int j, length, nsupport;
	unsigned short* pitemset;

	fp_stat = fopen("map.stat.txt", "a+");
	if(fp_stat==NULL)
	{
		printf("Error: cannot open file map.stat.txt for write\n");
		return;
	}
	fprintf(fp_stat, "%s\t%d %.f\n", goparameters.szdata_filename, gnmin_sup, gdtotal_generators);
	fprintf(fp_stat, "Map Size: %d\n", MAP_SIZE);
	fprintf(fp_stat, "\n");

	fp_long = fopen("map.long.txt", "wt");
	if(fp_long==NULL)
	{
		printf("Error: cannot open file map.long.txt for write\n");
		return;
	}

	num_of_maps = 0;
	davg_map_size = 0;
	nmax_map_size = 0;
	nmax_nonempty_entries = 0;
	davg_nonempty_entries = 0;
	nmax_map_depth = 0;
	davg_map_depth = 0;

	ppat_map = mppat_map;
	while(ppat_map!=NULL)
	{
		num_of_maps++;
		davg_map_size += ppat_map->num_of_nodes;
		if(nmax_map_size<ppat_map->num_of_nodes)
			nmax_map_size = ppat_map->num_of_nodes; 

		nlocal_nonempty_entries = 0;
		nlocal_max_map_depth = 0;
		dlocal_avg_map_depth = 0;
		for(i=0;i<MAP_SIZE;i++)
		{
			pmap_node = ppat_map->ppat_map_nodes[i];
			if(pmap_node!=NULL)
			{
				nlocal_nonempty_entries++;
				ndepth = 0;
				while(pmap_node!=NULL)
				{
					ndepth++;
					pmap_node = pmap_node->pnext;
				}

				if(ndepth>=10)
				{
					fprintf(fp_long, "%d\t%d\n", i, ndepth);
					pmap_node = ppat_map->ppat_map_nodes[i];
					while(pmap_node!=NULL)
					{
						length = pmap_node->ppattern[0];
						memcpy(&nsupport, &(pmap_node->ppattern[1]), sizeof(int));
						pitemset = &(pmap_node->ppattern[3]);
						nmap_value = HashItemset(pitemset, length);
						nhash_value = HashFunc(nmap_value);

						fprintf(fp_long, "%d %d\t%d %d\t", nmap_value, nhash_value, length, nsupport);
						for(j=0;j<length;j++)
							fprintf(fp_long, "%d ", pitemset[j]);
						fprintf(fp_long, "\n");
						pmap_node = pmap_node->pnext;
					}
					fprintf(fp_long, "\n\n");
				}

				dlocal_avg_map_depth += ndepth;
				if(nlocal_max_map_depth<ndepth)
					nlocal_max_map_depth = ndepth;
			}
		}
		if(nmax_nonempty_entries<nlocal_nonempty_entries)
			nmax_nonempty_entries = nlocal_nonempty_entries;
		davg_nonempty_entries += nlocal_nonempty_entries; 
		if(nmax_map_depth<nlocal_max_map_depth)
			nmax_map_depth = nlocal_max_map_depth;
		davg_map_depth += dlocal_avg_map_depth;

		fprintf(fp_stat, "%d\t%d\t%d\t\t%d (%.3f)\t\t%d\t%.2f\n", num_of_maps, ppat_map->nstart, ppat_map->num_of_nodes, nlocal_nonempty_entries, (double)nlocal_nonempty_entries/MAP_SIZE, nlocal_max_map_depth, dlocal_avg_map_depth/nlocal_nonempty_entries);

		ppat_map = ppat_map->pprev;
	}

	fprintf(fp_stat, "\n");
	fprintf(fp_stat, "%d\t%d\t%d\t\t%d (%.3f)\t\t%d\t%.2f\n", num_of_maps, gntotal_freqitems, nmax_map_size, nmax_nonempty_entries, (double)nmax_nonempty_entries/MAP_SIZE, nmax_map_depth, davg_map_depth/davg_nonempty_entries);
	fprintf(fp_stat, "\t\t%.2f\t%.2f (%.3f)\t", davg_map_size/num_of_maps, davg_nonempty_entries/num_of_maps, davg_nonempty_entries/(num_of_maps*MAP_SIZE));
	fprintf(fp_stat, "\n\n\n");

	fclose(fp_stat);
	fclose(fp_long);
}

