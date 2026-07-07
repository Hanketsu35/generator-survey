#pragma once 

/*----------------------------------------------------------------------
  File     : data.h
  Contents : data set management
----------------------------------------------------------------------*/

#include <stdio.h>
#include <stdlib.h>

#define INIT_TRANS_LEN  200

class Transaction
{
public:  
  int length;
  int *t;
};

class Data
{
 public:
	
  Data(char *filename);
  ~Data();
  int isOpen();

  Transaction* mptransaction;
  int micapacity;
  
  Transaction *getNextTransaction();
  
 private:
  
  FILE *in;
};

extern Data* gpdata;

