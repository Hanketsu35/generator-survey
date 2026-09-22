#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/timeb.h>

#include "ScanDBMine.h"
#include "FPtree.h"
#include "parameters.h"
#include "fsout.h"
#include "data.h"
#include "inline_routine.h"
#include "PatternSet.h"

FPNODE_BUF gofpnode_buf;
HEADER_TABLE gpheader_table;

HEADER_TABLE gpdfs_header_array;
int gndfs_header_size;
int gndfs_header_pos;

int IsGenerator(int nitem, int nsupport, int nsubsup1, int nsubsup2);
bool IsMinimal(int nitem);


int main(int argc, char *argv[])
{
	if(argc!=5 && argc!=4)
	{
		printf("Usage\n");
		printf("\t%s  data_filename  nmin_sup(an obsolute number) k [output_filename]\n", argv[0]);
		return 0;
	}

	snprintf(goparameters.szdata_filename, MAX_FILENAME_LEN, "%s", argv[1]);
	goparameters.nmin_sup = atoi(argv[2]);
	goparameters.k = atoi(argv[3]);
	gnmin_sup = goparameters.nmin_sup;

	if(goparameters.nmin_sup<1)
	{
		printf("Please specify a native number for the minimum support threshold\n");
		return 0;
	}
	if(argc==5)
	{
		goparameters.bresult_name_given = true;
		goparameters.SetResultName(argv[4]);
	}
	else 
		goparameters.bresult_name_given = false;

	MineFreqGenerators();

	return (int)gdtotal_generators;
}

void MineFreqGenerators()
{
	FP_NODE *proot;
	HEADER_TABLE pheader_table;
	int *pitem_sup_map, ncapacity, i, nfreq_item;

	struct timeb start, end;

	ftime(&start);

	if(goparameters.bresult_name_given)
	{
		gpfgout = new FSout(goparameters.szgenerator_filename);
		gpnbout = new FSout(goparameters.sznegborder_filename);
	}
	gpdata = new Data(goparameters.szdata_filename);

	gnmax_pattern_len = 0;
	gntotal_call = 0;
	gdused_mem_size = 0;
	gdmax_used_mem_size = 0;
	gntree_init_size = 0;
	gntree_max_size = 0;
	gdtotal_generators = 0;
	gdfreqborder_size = 0;
	gdnum_of_zerosets = 0;
	gngenerator_check_times = 0;
	gnnegborder_check_times = 0;
	gnmap_value = 0;

	//count frequent items in original database
	pitem_sup_map = NULL;
	ncapacity = goDBMiner.ScanDBCountFreqItems(pitem_sup_map);

	gpprefix_itemset = NewIntArray(gnmax_trans_len);
	gnprefix_len = 0;

	OutputOneGenerator(gndb_size);

	//enumerate frequent itemsets
	gntotal_freqitems  = 0;
	for(i=0;i<gnmax_item_id;i++)
	{
		if(pitem_sup_map[i]==gndb_size)
			OutputOneFBdPat(i, i, gndb_size);
		else if(pitem_sup_map[i]>=gnmin_sup)
		{
			gntotal_freqitems++;
			nfreq_item = i;
		}			
	}

	if(gntotal_freqitems==0)
	{
		gnmax_pattern_len = 0;
		delete gpdata;
		DelIntArray(pitem_sup_map, ncapacity);
	}
	else if(gntotal_freqitems==1)
	{
		OutputOneGenerator(nfreq_item, pitem_sup_map[nfreq_item]);

		gnmax_pattern_len = 1;
		delete gpdata;
		DelIntArray(pitem_sup_map, ncapacity);
	}
	else if(gntotal_freqitems>1)
	{
		pheader_table = NewHeaderTable(gntotal_freqitems);
		gntotal_freqitems = 0;
		for(i=0;i<gnmax_item_id;i++)
		{
			if(pitem_sup_map[i]>=gnmin_sup && pitem_sup_map[i]<gndb_size)
			{
				pheader_table[gntotal_freqitems].nitem = i;
				pheader_table[gntotal_freqitems].nsupport = pitem_sup_map[i];
				pheader_table[gntotal_freqitems].pconddb = NULL;
				gntotal_freqitems++;
			}
		}
		qsort(pheader_table, gntotal_freqitems, sizeof(HEADER_NODE), comp_item_freq_des);
		DelIntArray(pitem_sup_map, ncapacity);

		gpheader_table = pheader_table;

		gpitem_order_map = NewIntArray(gnmax_item_id, -1);
		for(i=0;i<gntotal_freqitems;i++)
			gpitem_order_map[pheader_table[i].nitem] =i;
		gpprefix_orderset = NewUShortArray(gnmax_trans_len);

		Init();
		gopatternset.Init();

		gnum_of_newfreqitems = gntotal_freqitems;

		proot = goDBMiner.ScanDBBuildFPtree(pheader_table, gpitem_order_map);
		gntree_init_size = sizeof(FPNODE_BUF)+gofpnode_buf.ntotal_pages*(sizeof(FP_NODE)*FPNODE_PAGE_SIZE+sizeof(FPNODE_PAGE));
		delete gpdata;

		gpdfs_item_suporder_map = NewIntArray(gntotal_freqitems);

		goFPtree.DepthFGGrowth(proot, pheader_table, gntotal_freqitems);

		DelIntArray(gpdfs_item_suporder_map, gntotal_freqitems);
		gntree_max_size = sizeof(FPNODE_BUF)+gofpnode_buf.ntotal_pages*(sizeof(FP_NODE)*FPNODE_PAGE_SIZE+sizeof(FPNODE_PAGE));
		Destroy();
		gopatternset.Destroy();
		DelIntArray(gpitem_order_map, gnmax_item_id);
		DelUShortArray(gpprefix_orderset, gnmax_trans_len);
		DelHeaderTable(pheader_table, gntotal_freqitems);
	}

	DelIntArray(gpprefix_itemset, gnmax_trans_len);

	if(goparameters.bresult_name_given)
	{
		delete gpfgout;
		delete gpnbout;
	}
	ftime(&end);
	gdtotal_running_time = end.time-start.time+(double)(end.millitm-start.millitm)/1000;

	PrintSummary();

}


void FPtree::DepthFGGrowth(FP_NODE *proot, HEADER_TABLE pheader_table, int num_of_freqitems)
{
	HEADER_TABLE pnewheader_table;
	FP_NODE *pnewroot, *pfpnode;
	FPNODE_PAGE *pstart_page;
	int k, i, j, nstart_pos, ncount, btype, nlen;

	gntotal_call++;

	for(k=0;k<num_of_freqitems;k++)
	{
		gpprefix_itemset[gnprefix_len] = pheader_table[k].nitem;
		gpprefix_orderset[gnprefix_len] = gpitem_order_map[pheader_table[k].nitem];
		gpitem_bitmap[gpprefix_orderset[gnprefix_len]] = 1;
		gnprefix_len++;
		gnmap_value = HashAdd1Item(gnmap_value, pheader_table[k].nitem);
		if(gnprefix_len==1)
			gopatternset.CheckMap(k);

		OutputOneGenerator(pheader_table[k].nsupport);
		gopatternset.Insert(pheader_table[k].nsupport);

		if(pheader_table[k].pconddb!=NULL)
		{
			if(pheader_table[k].pconddb->pnode_link==NULL)
			{
				ncount = pheader_table[k].pconddb->frequency;
				pfpnode = pheader_table[k].pconddb->pparent;
				if(ncount==pheader_table[k].nsupport)
				{
					while(pfpnode!=NULL)
					{
						if(gnprefix_len==1 || IsMinimal(pheader_table[pfpnode->nitem_order].nitem))
							OutputOneFBdPat(pheader_table[pfpnode->nitem_order].nitem, pheader_table[pfpnode->nitem_order].nitem, ncount);
						pfpnode = pfpnode->pparent;
					}
				}
				else if(ncount>=gnmin_sup)
				{
					nlen = 0;
					while(pfpnode!=NULL)
					{
						if(pheader_table[pfpnode->nitem_order].nsupport==ncount)
						{
							if(gnprefix_len==1 || IsMinimal(pheader_table[pfpnode->nitem_order].nitem))
								OutputOneFBdPat(pheader_table[pfpnode->nitem_order].nitem, pheader_table[k].nitem, ncount);
						}
						else if(gnprefix_len==1)
						{
							OutputOneGenerator(pheader_table[pfpnode->nitem_order].nitem, ncount);
							gopatternset.Insert(pheader_table[pfpnode->nitem_order].nitem, ncount);
							gpsingle_branch[nlen] = pheader_table[pfpnode->nitem_order].nitem;
							nlen++;
						}
						else 
						{
							btype = IsGenerator(pheader_table[pfpnode->nitem_order].nitem, ncount, pheader_table[pfpnode->nitem_order].nsupport, pheader_table[k].nsupport);
							if(btype==IS_GENERATOR)
							{
								OutputOneGenerator(pheader_table[pfpnode->nitem_order].nitem, ncount);
								gopatternset.Insert(pheader_table[pfpnode->nitem_order].nitem, ncount);
								gpsingle_branch[nlen] = pheader_table[pfpnode->nitem_order].nitem;
								nlen++;
							}
							else if(btype==IS_FREQBORDER)
								OutputOneFBdPat(pheader_table[pfpnode->nitem_order].nitem, gnrdnt_item, ncount);
						}
						pfpnode = pfpnode->pparent;
					}
					if(nlen>1)
					{
						for(i=0;i<nlen-1;i++)
						{
							gpprefix_itemset[gnprefix_len] = gpsingle_branch[i];
							gpprefix_orderset[gnprefix_len] = gpitem_order_map[gpsingle_branch[i]];
							gpitem_bitmap[gpprefix_orderset[gnprefix_len]] = 1;
							gnprefix_len++;
							gnmap_value = HashAdd1Item(gnmap_value, gpsingle_branch[i]);
							for(j=i+1;j<nlen;j++)
							{
								if(IsMinimal(gpsingle_branch[j]))
									OutputOneFBdPat(gpsingle_branch[j], gpsingle_branch[j], ncount);
							}
							gnprefix_len--;
							gpitem_bitmap[gpprefix_orderset[gnprefix_len]] = 0;
							gnmap_value = HashRemove1Item(gnmap_value, gpsingle_branch[i]);
						}
					}
				}
			}
			else
			{
				//count frequent items from AFOPT-tree
				memset(gpdfs_item_suporder_map, 0, sizeof(int)*k);
				CountFreqItems(pheader_table, k, gpdfs_item_suporder_map);

				pnewheader_table = NewHeaderTable(k);
				gnum_of_newfreqitems = 0;
				for(i=0;i<k;i++)
				{
					if(gpdfs_item_suporder_map[i]==pheader_table[k].nsupport)
					{
						if(gnprefix_len==1 || IsMinimal(pheader_table[i].nitem))
							OutputOneFBdPat(pheader_table[i].nitem, pheader_table[i].nitem, gpdfs_item_suporder_map[i]);
					}
					else if(gpdfs_item_suporder_map[i]==pheader_table[i].nsupport)
					{
						if(gnprefix_len==1 || IsMinimal(pheader_table[i].nitem))
							OutputOneFBdPat(pheader_table[i].nitem, pheader_table[k].nitem, gpdfs_item_suporder_map[i]);
					}
					else if(gpdfs_item_suporder_map[i]>=gnmin_sup)
					{
						if(gnprefix_len==1 && goparameters.k==1)
						{
							pnewheader_table[gnum_of_newfreqitems].nitem = pheader_table[i].nitem;
							pnewheader_table[gnum_of_newfreqitems].nsupport = gpdfs_item_suporder_map[i];
							pnewheader_table[gnum_of_newfreqitems].pconddb = NULL;
							pnewheader_table[gnum_of_newfreqitems].order = i;
							gnum_of_newfreqitems++;
						}
						else
						{
							 btype = IsGenerator(pheader_table[i].nitem, gpdfs_item_suporder_map[i], pheader_table[i].nsupport, pheader_table[k].nsupport);
							 if(btype==IS_GENERATOR)
							 {
								pnewheader_table[gnum_of_newfreqitems].nitem = pheader_table[i].nitem;
								pnewheader_table[gnum_of_newfreqitems].nsupport = gpdfs_item_suporder_map[i];
								pnewheader_table[gnum_of_newfreqitems].pconddb = NULL;
								pnewheader_table[gnum_of_newfreqitems].order = i;
								gnum_of_newfreqitems++;
							 }
							 else if(btype==IS_FREQBORDER)
								 OutputOneFBdPat(pheader_table[i].nitem, gnrdnt_item, gpdfs_item_suporder_map[i]);
						}
					}
					gpdfs_item_suporder_map[i] = -1;
				}
				if(gnum_of_newfreqitems>1)
				{
					qsort(pnewheader_table, gnum_of_newfreqitems, sizeof(HEADER_NODE), comp_item_freq_des);
					for(i=0;i<gnum_of_newfreqitems;i++)
						gpdfs_item_suporder_map[pnewheader_table[i].order] = i;
				}

				if(gnum_of_newfreqitems==1)
				{
					OutputOneGenerator(pnewheader_table[0].nitem, pnewheader_table[0].nsupport);
					gopatternset.Insert(pnewheader_table[0].nitem, pnewheader_table[0].nsupport);
				}
				else if(gnum_of_newfreqitems>1)
				{
					pstart_page = gofpnode_buf.pcur_page;
					nstart_pos = gofpnode_buf.ncur_pos;
					pnewroot = BuildNewFPTree(pheader_table[k].pconddb, pnewheader_table, gpdfs_item_suporder_map); 

					DepthFGGrowth(pnewroot, pnewheader_table, gnum_of_newfreqitems);

					Reset(pstart_page, nstart_pos);
				}
				DelHeaderTable(pnewheader_table, k);
			}
		}
		gnprefix_len--;
		gpitem_bitmap[gpprefix_orderset[gnprefix_len]] = 0;
		gnmap_value = HashRemove1Item(gnmap_value, pheader_table[k].nitem);
	}

}


int IsGenerator(int nitem, int nsupport, int nsubsup1, int nsubsup2)
{
	int btype;

	gngenerator_check_times++;

	gpitem_bitmap[gpitem_order_map[nitem]] = 1;
	gpprefix_itemset[gnprefix_len] = nitem;
	gpprefix_orderset[gnprefix_len] = gpitem_order_map[nitem];

	if(goparameters.k==1)
		btype = gopatternset.IsGenerator(nitem, nsupport);
	else 
		btype = gopatternset.IskFree(nitem, nsupport, nsubsup1, nsubsup2);

	gpitem_bitmap[gpitem_order_map[nitem]] = 0;

//	if(btype==IS_FREQBORDER && gnprefix_len>1 && !IsMinimal(nitem))
//		printf("Error: inconsistent of frequent border\n");

	return btype;

}

bool IsMinimal(int nitem)
{
	bool bisminimal; 

	gnnegborder_check_times++;

	gpitem_bitmap[gpitem_order_map[nitem]] = 1;

	bisminimal = gopatternset.IsMinimal(nitem);

	gpitem_bitmap[gpitem_order_map[nitem]] = 0;

	return bisminimal;
}


void PrintSummary()
{
	printf("#generators: %.f\tfrequent border size: %.f\n", gdtotal_generators, gdfreqborder_size);
	if(gdused_mem_size!=0)
		printf("Error with memory: %.2f are not released\n", gdused_mem_size);

	FILE *fp_sum;

	fp_sum = fopen("fg.fbd.sum.txt", "a+");
	if(fp_sum == NULL)
	{
		printf("Error[PrintSummary]: cannot open file fg.sum.txt\n");
		return;
	}
	fprintf(fp_sum, "FGGrowth-FBd %s ", goparameters.szdata_filename);
	fprintf(fp_sum, "%f %d  ", (double)goparameters.nmin_sup*100/gndb_size, goparameters.k);
	fprintf(fp_sum, "%d %.f %.f %d  %.f %d\t", gnmax_pattern_len, gdtotal_generators+gdfreqborder_size, gdtotal_generators, gngenerator_check_times, gdfreqborder_size, gnnegborder_check_times);
	fprintf(fp_sum, "%.2f\t", gdtotal_running_time);
	fprintf(fp_sum, "%.2fMB %.2fMB %.2fMB\t", gdmax_used_mem_size/(1<<20), (double)gntree_init_size/(1<<20), (double)gntree_max_size/(1<<20));

//	gopatternset.PrintMapStatis(fp_sum);

	fprintf(fp_sum, "\n");
	fclose(fp_sum);
}

