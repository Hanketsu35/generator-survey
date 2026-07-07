#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/timeb.h>

#include "global.h"
#include "pat_map.h"
#include "fsout.h"

FREQ_ITEM* gpfreqitems;
int gnum_of_freqitems;
int* gpitem_order_map;
int* gpprefix_itemset;
int gnprefix_len;
int* gpcover_items;
int gnum_of_cover_items;
unsigned int gnmap_value;
int* gpitem_bitmap;

int gnmax_key_len;
int gnmax_item_id;
int gndb_size;

double gdtotal_pats;
int gnmax_pat_len;
int* gpstack;

bool *gprdnt_flags;
int gntotal_rdnt_items;
int *gprdnt_item_positions;
int gnrdnt_item_num;


HEADER_TABLE gpdfs_header_array;
int gndfs_header_size;
int gndfs_header_pos;

INT_PAGE_BUF gordnt_item_buf;

double gdFG_load_time;
double gdFBd_load_time;
double gdtotal_running_time;
int gntotal_search_times;
int gntotal_freq_checkes;


void DFSRecoverFI(HEADER_TABLE pheader_table, int num_of_freqitems);
void OutputPats(int nsupport);
int GetItemsetSup(int nitem, int nprefix_sup);
void LoadCoverItems(char* szcoveritem_filename);
void PrintSum(char* szkey_filename, char* szbd_filename);


void RecoverFI(char* szfreqkey_filename, char* szbd_filename, char* szcoveritem_filename, char* szoutput_filename)
{
	HEADER_TABLE pheader_table;
	int i;
	struct timeb start, end;

	ftime(&start);

	gnmax_item_id = 0;

	gofreqkey_map.BuildPatHashMap(szfreqkey_filename, 0);
	ftime(&end);
	gdFG_load_time = end.time-start.time+(double)(end.millitm-start.millitm)/1000;

	gpprefix_itemset = new int[gnmax_key_len+100];
	gnprefix_len = 0;
	gprdnt_flags = new bool[gnmax_key_len];
	gntotal_rdnt_items = 0;
	gpcover_items = new int[100];
	gnum_of_cover_items = 0;
	gpstack = new int[100];
	gntotal_search_times = 0;
	gntotal_freq_checkes = 0;

	gdtotal_pats = 0;
	gnmax_pat_len = 0;
	gnmap_value = 0;

	if(gnrep_type==0)
		gobd_map.BuildPatHashMap(szbd_filename, 1);
	else if(gnrep_type==1)
	{
		gobd_map.BuildPatHashMap(szbd_filename, 2);
		LoadCoverItems(szcoveritem_filename);
	}
	gdFBd_load_time = end.time-start.time+(double)(end.millitm-start.millitm)/1000;
	gdFBd_load_time -= gdFG_load_time;


	if(szoutput_filename!=NULL)
		gpfout = new FSout(szoutput_filename);
	else 
		gpfout = NULL;

	OutputPats(gndb_size);
	if(gnum_of_freqitems==1)
	{
		gpprefix_itemset[gnprefix_len++] = gpfreqitems[0].nitem;
		OutputPats(gpfreqitems[0].nsup);
		gnprefix_len--;
	}
	else if(gnum_of_freqitems>1)
	{
		gndfs_header_size = gnum_of_freqitems*5;
		gpdfs_header_array = new HEADER_NODE[gndfs_header_size];
		gndfs_header_pos = 0;
		gpitem_bitmap = new int[gnmax_item_id];
		memset(gpitem_bitmap, -1, sizeof(int)*gnmax_item_id);
		gprdnt_item_positions = new int[100];

		pheader_table = new HEADER_NODE[gnum_of_freqitems];
		for(i=0;i<gnum_of_freqitems;i++)
		{
			pheader_table[i].nitem = gpfreqitems[i].nitem;
			pheader_table[i].nsup = gpfreqitems[i].nsup;
			pheader_table[i].num_of_rdnt_items = 0;
			pheader_table[i].prdnt_items = NULL;
		}

		gordnt_item_buf.phead = NewIntPage();
		gordnt_item_buf.pcur_page = gordnt_item_buf.phead;
		gordnt_item_buf.ncur_pos = 0;
		gordnt_item_buf.ntotal_pages = 1;

		DFSRecoverFI(pheader_table, gnum_of_freqitems);

		DelIntBuf(&gordnt_item_buf);

		delete []pheader_table;
		delete []gprdnt_item_positions;
		delete []gpitem_bitmap;
		delete []gpdfs_header_array;
	}

	if(gpfout!=NULL)
		delete gpfout;
	delete []gpprefix_itemset;
	delete []gprdnt_flags;
	delete []gpcover_items;
	delete []gpfreqitems;
	delete []gpitem_order_map;
	delete []gpstack;
	gofreqkey_map.DelPatMap();
	gobd_map.DelPatMap();

	ftime(&end);
	gdtotal_running_time = end.time-start.time+(double)(end.millitm-start.millitm)/1000;

	PrintSum(szfreqkey_filename, szbd_filename);

	printf("#patterns: %.f\n", gdtotal_pats);
	//printf("Total running time: %f\n", gdtotal_running_time);
	//printf("FG loading time: %f\n", gdFG_load_time);
	//printf("FBd loading time: %f\n", gdFBd_load_time);
	//printf("Total search times: %d\n", gntotal_search_times);
}


void DFSRecoverFI(HEADER_TABLE pheader_table, int num_of_freqitems)
{
	HEADER_TABLE pnew_header_table;
	int i, j, nsup, num_of_cover_items, num_of_newfreq_items, nitem;
	unsigned int norig_map_value;
	INT_PAGE *porig_page;
	int norig_page_pos;

	for(i=0;i<num_of_freqitems;i++)
	{
		gpprefix_itemset[gnprefix_len] = pheader_table[i].nitem;
		gprdnt_flags[gnprefix_len] = false;
		gpitem_bitmap[pheader_table[i].nitem] = gnprefix_len;
		gnprefix_len++;
		norig_map_value = gnmap_value;
		gnmap_value = HashAdd1Item(gnmap_value, pheader_table[i].nitem);

//if(gnprefix_len==3 && gpprefix_itemset[0]==2 && gpprefix_itemset[1]==59 && gpprefix_itemset[2]==90)
//   gpprefix_itemset[3]==39 && gpprefix_itemset[4]==86 && gpprefix_itemset[5]==2 && gpprefix_itemset[6]==59)
//printf("stop\n");

		if(i==0)
			OutputPats(pheader_table[i].nsup);
		else if(i>0)
		{
			if(pheader_table[i].num_of_rdnt_items>0)
			{
				gntotal_rdnt_items += pheader_table[i].num_of_rdnt_items;
				for(j=0;j<pheader_table[i].num_of_rdnt_items;j++)
				{
					gprdnt_flags[pheader_table[i].prdnt_items[j]] = true;
					nitem = gpprefix_itemset[pheader_table[i].prdnt_items[j]];
					gnmap_value = HashRemove1Item(gnmap_value, nitem);
					gpitem_bitmap[nitem] = -1;
				}
			}
			porig_page = gordnt_item_buf.pcur_page;
			norig_page_pos = gordnt_item_buf.ncur_pos;

			pnew_header_table = NewHeaderTable(i);
			num_of_cover_items = 0;
			num_of_newfreq_items = 0;
			for(j=0;j<i;j++)
			{
				nsup = GetItemsetSup(pheader_table[j].nitem, pheader_table[i].nsup);
				if(nsup==pheader_table[i].nsup)
				{
					gpcover_items[gnum_of_cover_items++] = pheader_table[j].nitem;
					num_of_cover_items++;
				}
				else if(nsup>0)
				{
					pnew_header_table[num_of_newfreq_items].nitem = pheader_table[j].nitem;
					pnew_header_table[num_of_newfreq_items].nsup = nsup;
					pnew_header_table[num_of_newfreq_items].num_of_rdnt_items = gnrdnt_item_num;
					if(gnrdnt_item_num>0)
					{
						pnew_header_table[num_of_newfreq_items].prdnt_items = NewOneIntArray(gnrdnt_item_num);
						memcpy(pnew_header_table[num_of_newfreq_items].prdnt_items, gprdnt_item_positions, sizeof(int)*gnrdnt_item_num);
					}
					else 
						pnew_header_table[num_of_newfreq_items].prdnt_items = NULL;
					num_of_newfreq_items++;
				}
			}
			if(num_of_newfreq_items>1)
				qsort(pnew_header_table, num_of_newfreq_items, sizeof(HEADER_NODE), comp_headernodes);

			OutputPats(pheader_table[i].nsup);

			if(num_of_newfreq_items==1)
			{
				gpprefix_itemset[gnprefix_len++] = pnew_header_table[0].nitem;
				OutputPats(pnew_header_table[0].nsup);
				gnprefix_len--;
			}
			else if(num_of_newfreq_items>1)
			{
				DFSRecoverFI(pnew_header_table, num_of_newfreq_items);
			}

			DelHeaderTable(pnew_header_table, i);

			gordnt_item_buf.pcur_page = porig_page;
			gordnt_item_buf.ncur_pos = norig_page_pos;

			gnum_of_cover_items -= num_of_cover_items;
			if(pheader_table[i].num_of_rdnt_items>0)
			{
				gntotal_rdnt_items -= pheader_table[i].num_of_rdnt_items;
				for(j=0;j<pheader_table[i].num_of_rdnt_items;j++)
				{
					gprdnt_flags[pheader_table[i].prdnt_items[j]] = false;
					nitem = gpprefix_itemset[pheader_table[i].prdnt_items[j]];
					gpitem_bitmap[nitem] = pheader_table[i].prdnt_items[j];
				}
			}
		}
		gnprefix_len--;
		gpitem_bitmap[pheader_table[i].nitem] = -1;
		gnmap_value = norig_map_value;
	}
}


void OutputPats(int nsupport)
{
	int ntop, norig_prefix_len;

	if(gpfout==NULL)
	{
		gdtotal_pats += (1<<gnum_of_cover_items);
		if(gnmax_pat_len<gnprefix_len+gnum_of_cover_items)
			gnmax_pat_len = gnprefix_len+gnum_of_cover_items;
		return;
	}

	OutputOnePat(nsupport);
	if(gnum_of_cover_items==1)
	{
		gpprefix_itemset[gnprefix_len++] = gpcover_items[0];
		OutputOnePat(nsupport);
		gnprefix_len--;
	}
	else if(gnum_of_cover_items>1)
	{
		norig_prefix_len = gnprefix_len;

		ntop = 0;
		gpstack[ntop++] = 0;
		gpprefix_itemset[gnprefix_len++] = gpcover_items[0];
		while(ntop>0)
		{
			OutputOnePat(nsupport);
			if(gpstack[ntop-1]<gnum_of_cover_items-1)
			{
				gpstack[ntop] = gpstack[ntop-1]+1;
				gpprefix_itemset[gnprefix_len++] = gpcover_items[gpstack[ntop]];
				ntop++;
			}
			else 
			{
				ntop--;
				gnprefix_len--;
				if(ntop>0)
				{
					gpstack[ntop-1]++;
					gpprefix_itemset[gnprefix_len-1] = gpcover_items[gpstack[ntop-1]];
				}
			}	
		}
		if(gnprefix_len!=norig_prefix_len)
		{
			printf("Error with the value of variable gnprefix_len\n");
			gnprefix_len = norig_prefix_len;
		}
	}
}

int FBdSearchSubset(int npos, int npat_len)
{
	int i, nsup, nmax_rdnt_pos, nrdnt_pos;
	bool bisfreq;

	bisfreq = false;
	nmax_rdnt_pos = -1;
	for(i=npos+1;i<gnprefix_len-1;i++)
	{
		if(gpitem_bitmap[gpprefix_itemset[i]]>=0)
		{
			gpitem_bitmap[gpprefix_itemset[i]] = -1;
			gnmap_value = HashRemove1Item(gnmap_value, gpprefix_itemset[i]);

			nsup = gobd_map.SearchPat(npat_len-1-gnrdnt_item_num);
			if(nsup>0)
			{
				nrdnt_pos = gnrdnt_item_pos;
				if(nmax_rdnt_pos<gnrdnt_item_pos)
					nmax_rdnt_pos = gnrdnt_item_pos;
				gprdnt_item_positions[gnrdnt_item_num++] = gnrdnt_item_pos;
				gpitem_bitmap[gpprefix_itemset[gnrdnt_item_pos]] = -1;
				gnmap_value = HashRemove1Item(gnmap_value, gpprefix_itemset[gnrdnt_item_pos]);
			}
			else 
				nsup = gofreqkey_map.SearchPat(npat_len-1-gnrdnt_item_num);
			if(nsup==-1 && i<gnprefix_len-2)
			{
				nrdnt_pos = FBdSearchSubset(i, npat_len-1);
				if(nmax_rdnt_pos<nrdnt_pos)
					nmax_rdnt_pos = nrdnt_pos;
			}

			gpitem_bitmap[gpprefix_itemset[i]] = i;
			gnmap_value = HashAdd1Item(gnmap_value, gpprefix_itemset[i]);

			while(nrdnt_pos>i)
			{
				nrdnt_pos = -1;
				nsup = gobd_map.SearchPat(npat_len-gnrdnt_item_num);
				if(nsup>0)
				{
					nrdnt_pos = gnrdnt_item_pos;
					gprdnt_item_positions[gnrdnt_item_num++] = gnrdnt_item_pos;
					gpitem_bitmap[gpprefix_itemset[gnrdnt_item_pos]] = -1;
					gnmap_value = HashRemove1Item(gnmap_value, gpprefix_itemset[gnrdnt_item_pos]);
				}
				else 
				{
					nsup = gofreqkey_map.SearchPat(npat_len-gnrdnt_item_num);
					if(nsup>0)
						bisfreq = true;
				}
			}
			if(bisfreq)
				break;
		}
	}
	return nmax_rdnt_pos;
}


int GetItemsetSupFBd(int nitem)
{
	int nsup, i, npat_len, nmax_rdnt_pos;
	unsigned int norig_map_value;
	bool bisfreq;

	gpprefix_itemset[gnprefix_len] = nitem;
	gprdnt_flags[gnprefix_len] = false;
	gpitem_bitmap[nitem] = gnprefix_len;
	gnprefix_len++;
	norig_map_value = gnmap_value;
	gnmap_value = HashAdd1Item(gnmap_value, nitem);

	if(gobd_map.mnum_of_pats==0)
		nsup = gofreqkey_map.SearchPat(gnprefix_len);
	else
	{
		gnrdnt_item_num = 0;

		npat_len = gnprefix_len-gntotal_rdnt_items;

		nsup = gofreqkey_map.SearchPat(npat_len);
		if(nsup==-1)
		{
			nsup = gobd_map.SearchPat(npat_len);
			if(nsup>0)
			{
				gprdnt_item_positions[0] = gnrdnt_item_pos;
				gnrdnt_item_num = 1;
			}
		}

		if(nsup==-1)
		{
			bisfreq = false;
			for(i=0;i<gnprefix_len-1;i++)
			{
				if(gpitem_bitmap[gpprefix_itemset[i]]>=0)
				{
					nmax_rdnt_pos = -1;
					gpitem_bitmap[gpprefix_itemset[i]] = -1;
					gnmap_value = HashRemove1Item(gnmap_value, gpprefix_itemset[i]);

					nsup = gobd_map.SearchPat(npat_len-1-gnrdnt_item_num);
					if(nsup>0)
					{
						nmax_rdnt_pos = gnrdnt_item_pos;
						gprdnt_item_positions[gnrdnt_item_num++] = gnrdnt_item_pos;
						gpitem_bitmap[gpprefix_itemset[gnrdnt_item_pos]] = -1;
						gnmap_value = HashRemove1Item(gnmap_value, gpprefix_itemset[gnrdnt_item_pos]);
					}
					else 
						nsup = gofreqkey_map.SearchPat(npat_len-1-gnrdnt_item_num);

					if(nsup==-1 && i<gnprefix_len-2)
						nmax_rdnt_pos = FBdSearchSubset(i, npat_len-1);

					gpitem_bitmap[gpprefix_itemset[i]] = i;
					gnmap_value = HashAdd1Item(gnmap_value, gpprefix_itemset[i]);

					while(nmax_rdnt_pos>i)
					{
						nmax_rdnt_pos = -1;
						nsup = gobd_map.SearchPat(npat_len-gnrdnt_item_num);
						if(nsup>0)
						{
							nmax_rdnt_pos = gnrdnt_item_pos;
							gprdnt_item_positions[gnrdnt_item_num++] = gnrdnt_item_pos;
							gpitem_bitmap[gpprefix_itemset[gnrdnt_item_pos]] = -1;
							gnmap_value = HashRemove1Item(gnmap_value, gpprefix_itemset[gnrdnt_item_pos]);
						}
						else 
						{
							nsup = gofreqkey_map.SearchPat(npat_len-gnrdnt_item_num);
							if(nsup>0)
								bisfreq = true;
						}
					}
					if(bisfreq)
						break;
				}
			}
			if(!bisfreq)
				nsup = gofreqkey_map.SearchPat(npat_len-gnrdnt_item_num);
		}
	}

	gnprefix_len--;
	gnmap_value = norig_map_value;
	for(i=0;i<gnrdnt_item_num;i++)
		gpitem_bitmap[gpprefix_itemset[gprdnt_item_positions[i]]] = gprdnt_item_positions[i];
	gpitem_bitmap[nitem] = -1;

	return nsup;
}

bool NBdSearchSubset(int npos, int npat_len, int &nmin_sup)
{
	int nsup, i;
	bool bis_infreq;

	bis_infreq = false;
	for(i=npos;i<gnprefix_len-1;i++)
	{
		gpitem_bitmap[gpprefix_itemset[i]] = -1;
		gnmap_value = HashRemove1Item(gnmap_value, gpprefix_itemset[i]);

		nsup = gofreqkey_map.SearchPat(npat_len-1);
		if(nsup>0)
		{
			if(nmin_sup>nsup)
				nmin_sup = nsup;
		}
		else
		{
			nsup = gobd_map.SearchPat(npat_len-1);
			if(nsup>=0)
				bis_infreq = true;
			else if(i<gnprefix_len-2)
				bis_infreq = NBdSearchSubset(i+1, npat_len-1, nmin_sup);
		}

		gpitem_bitmap[gpprefix_itemset[i]] = i;
		gnmap_value = HashAdd1Item(gnmap_value, gpprefix_itemset[i]);
		if(bis_infreq)
			break;
	}

	return bis_infreq;
}

int GetItemsetSupNBd(int nitem, int nprefix_sup)
{
	int nsup, nmin_sup;
	unsigned int norig_map_value;
	bool bis_infreq;

	gpprefix_itemset[gnprefix_len] = nitem;
	gpitem_bitmap[nitem] = gnprefix_len;
	gnprefix_len++;
	norig_map_value = gnmap_value;
	gnmap_value = HashAdd1Item(gnmap_value, nitem);

	if(gntotal_rdnt_items!=0)
		printf("Error\n");

	bis_infreq = false;
	nsup = gofreqkey_map.SearchPat(gnprefix_len);
	if(nsup==-1)
	{
		nsup = gobd_map.SearchPat(gnprefix_len);
		if(nsup>=0)
		{
			bis_infreq = true;
			nsup = -1;
		}
		else
		{
			nmin_sup = nprefix_sup;
			bis_infreq = NBdSearchSubset(0, gnprefix_len, nmin_sup);
			if(bis_infreq)
				nsup = -1;
			else
				nsup = nmin_sup;
		}
	}

	gnprefix_len--;
	gnmap_value = norig_map_value;
	gpitem_bitmap[nitem] = -1;

	return nsup;
}

int GetItemsetSup(int nitem, int nprefix_sup)
{
	int nsup;

	gntotal_search_times++;
	if(gnrep_type==0)
		nsup = GetItemsetSupFBd(nitem);
	else
		nsup = GetItemsetSupNBd(nitem, nprefix_sup);
	if(nsup>0)
		gntotal_freq_checkes++;

	return nsup;

}

void DelIntBuf(INT_PAGE_BUF *prdnt_item_buf)
{
	INT_PAGE *ppage;

	ppage = prdnt_item_buf->phead;
	while(ppage!=NULL)
	{
		prdnt_item_buf->phead = ppage->pnext;
		DelIntPage(ppage);
		prdnt_item_buf->ntotal_pages--;

		ppage = prdnt_item_buf->phead;
	}
	if(prdnt_item_buf->ntotal_pages!=0)
		printf("Error: inconsistent number of pages\n");
}

void LoadCoverItems(char* szcoveritem_filename)
{
	FILE *fp;
	int nitem;

	fp = fopen(szcoveritem_filename, "rt");
	if(fp==NULL)
	{
		printf("Error: cannot open file %s for read\n", szcoveritem_filename);
		return;
	}

	nitem = GetNextNum(fp);
	while(!feof(fp))
	{
		gpcover_items[gnum_of_cover_items++] = nitem;
		nitem = GetNextNum(fp);
	}
	fclose(fp);

}

void PrintSum(char* szkey_filename, char* szbd_filename)
{
	FILE *fp;

	fp = fopen("recover_fi.sum.txt", "a+");
	if(fp==NULL)
	{
		printf("Error: cannot open file recover_fi.sum.txt for appending\n");
		return;
	}
	
	fprintf(fp, "%s %s\t", szkey_filename, szbd_filename);
	fprintf(fp, "%d %d\t", gntotal_search_times, gntotal_freq_checkes);
	fprintf(fp, "%.2f %.2f %.2f\n", gdtotal_running_time, gdFG_load_time, gdFBd_load_time);
	fclose(fp);
}

int comp_freqitems(const void* e1, const void* e2)
{
	FREQ_ITEM *p1, *p2;

	p1 = (FREQ_ITEM*)e1;
	p2 = (FREQ_ITEM*)e2;

	if(p1->nsup < p2->nsup)
		return 1;
	else if(p1->nsup > p2->nsup)
		return -1;
	else
		return 0;
}

int comp_headernodes(const void* e1, const void* e2)
{
	HEADER_NODE *p1, *p2;

	p1 = (HEADER_NODE*)e1;
	p2 = (HEADER_NODE*)e2;

	if(p1->nsup < p2->nsup)
		return 1;
	else if(p1->nsup > p2->nsup)
		return -1;
	else
		return 0;
}

