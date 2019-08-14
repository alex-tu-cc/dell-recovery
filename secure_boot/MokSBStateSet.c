/** @file

  Copyright (c) 2016, Canonical Limited. All rights reserved.

  This program and the accompanying materials
  are licensed and made available under the terms and conditions of the BSD License
  which accompanies this distribution.  The full text of the license may be found at
  http://opensource.org/licenses/bsd-license.php

  THE PROGRAM IS DISTRIBUTED UNDER THE BSD LICENSE ON AN "AS IS" BASIS,
  WITHOUT WARRANTIES OR REPRESENTATIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.

**/

#include <efi.h>
#include <efilib.h>

#define  MOKSBSTATE_GUID    \
{ 0x605DAB50, 0xE046, 0x4300, {0xab, 0xb6, 0x3d, 0xd8, 0x10, 0xdd, 0x8b, 0x23}}

EFI_STATUS
efi_main(EFI_HANDLE image, EFI_SYSTEM_TABLE *systab)
{
  UINT32        VariableAttrBT;
  UINT32        VariableAttrRT;
  EFI_GUID      VariableMoksbGuid = MOKSBSTATE_GUID;
  EFI_STATUS    efi_status;
  UINT8         Data=1;
  VariableAttrBT = (EFI_VARIABLE_NON_VOLATILE|EFI_VARIABLE_BOOTSERVICE_ACCESS);
  VariableAttrRT = (EFI_VARIABLE_NON_VOLATILE | EFI_VARIABLE_BOOTSERVICE_ACCESS | EFI_VARIABLE_RUNTIME_ACCESS);

  InitializeLib(image, systab);

  efi_status = uefi_call_wrapper(RT->SetVariable, 5,
                    L"MokSBState",
                    &VariableMoksbGuid,
                    VariableAttrBT,
                    1,
                    &Data
                  );
  if (efi_status != EFI_SUCCESS) {
    Print(L"Error writing MokSBState variable\n");
  }
  else {
    Print(L"Wrote MokSBState variable\n");
  }

  efi_status = uefi_call_wrapper(RT->SetVariable, 5,
                    L"MokSBStateRT",
                    &VariableMoksbGuid,
                    VariableAttrRT,
                    1,
                    &Data
                  );

  if (efi_status != EFI_SUCCESS) {
    Print(L"Error writing MokSBStateRT variable\n");
  }
  else {
    Print(L"Wrote MokSBStateRT variable\n");
  }

  uefi_call_wrapper(BS->Stall, 1, 2000000);

  uefi_call_wrapper(RT->ResetSystem, 4, EfiResetWarm, EFI_SUCCESS,
                    0, NULL);

  return EFI_SUCCESS;
}
